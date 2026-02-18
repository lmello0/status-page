from dataclasses import replace
from datetime import datetime, timezone

import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.page import Page
from core.domain.product import Product
from core.domain.status_type import StatusType
from core.exceptions.product_not_found_error import ProductNotFoundError
from infra.web.routers.schemas.product import ProductCreateDTO, ProductUpdateDTO
from tests.support.fakes import FakeLogRepository, FakeProductRepository
from use_cases.product.create_product_use_case import CreateProductUseCase
from use_cases.product.delete_product_use_case import DeleteProductUseCase
from use_cases.product.get_all_products_use_case import GetAllProductsUseCase
from use_cases.product.get_product_by_id_use_case import GetProductByIdUseCase
from use_cases.product.get_product_by_name_use_case import GetProductByNameUseCase
from use_cases.product.update_product_use_case import UpdateProductUseCase


def _component(component_id: int, name: str) -> Component:
    return Component(
        id=component_id,
        product_id=1,
        name=name,
        type=ComponentType.BACKEND,
        monitoring_config=HealthcheckConfig(health_url=f"https://{name}.example.com/health"),
        current_status=StatusType.OPERATIONAL,
    )


@pytest.mark.asyncio
async def test_create_product_use_case_builds_visible_product_and_persists() -> None:
    repository = FakeProductRepository()
    use_case = CreateProductUseCase(repository)

    created = await use_case.execute(ProductCreateDTO(name="API", description="Main API"))

    assert created.id is not None
    assert created.name == "API"
    assert created.description == "Main API"
    assert created.is_visible is True


@pytest.mark.asyncio
async def test_get_product_by_id_raises_when_missing() -> None:
    use_case = GetProductByIdUseCase(FakeProductRepository())

    with pytest.raises(ProductNotFoundError):
        await use_case.execute(999)


@pytest.mark.asyncio
async def test_get_product_by_name_raises_when_missing() -> None:
    use_case = GetProductByNameUseCase(FakeProductRepository())

    with pytest.raises(ProductNotFoundError):
        await use_case.execute("missing")


@pytest.mark.asyncio
async def test_update_product_updates_only_supplied_fields() -> None:
    repository = FakeProductRepository(
        initial_products=[
            Product(id=10, name="API", description="old", is_visible=True),
        ]
    )
    use_case = UpdateProductUseCase(repository)

    updated = await use_case.execute(10, ProductUpdateDTO(description="new"))

    assert updated.id == 10
    assert updated.name == "API"
    assert updated.description == "new"


@pytest.mark.asyncio
async def test_delete_product_use_case_returns_repository_result() -> None:
    repository = FakeProductRepository(
        initial_products=[Product(id=1, name="API")]
    )
    use_case = DeleteProductUseCase(repository)

    result = await use_case.execute(1)

    assert result is True


@pytest.mark.asyncio
async def test_get_all_products_enriches_component_summaries_and_dedupes_ids() -> None:
    shared_component = _component(100, "shared")
    other_component = _component(200, "other")

    first = Product(id=1, name="A", components=[shared_component, other_component], is_visible=True)
    second = Product(id=2, name="B", components=[replace(shared_component, product_id=2)], is_visible=True)

    product_repository = FakeProductRepository(initial_products=[first, second])
    precomputed_summary = {
        100: [
            HealthcheckLogDaySummary(
                component_id=100,
                date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                total_checks=4,
                successful_checks=4,
                uptime=100.0,
                avg_response_time=20,
                max_response_time=30,
                overall_status=StatusType.OPERATIONAL,
            )
        ],
        200: [
            HealthcheckLogDaySummary(
                component_id=200,
                date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                total_checks=4,
                successful_checks=2,
                uptime=50.0,
                avg_response_time=70,
                max_response_time=90,
                overall_status=StatusType.DEGRADED,
            )
        ],
    }
    log_repository = FakeLogRepository(precomputed_summary=precomputed_summary)

    use_case = GetAllProductsUseCase(product_repository=product_repository, log_repository=log_repository)
    result: Page[Product] = await use_case.execute(is_visible=True, page=0, page_size=0, summary_days=7)

    assert result.page_size == 10
    assert result.page_count == 2
    assert log_repository.bulk_calls == [([100, 200], 7)]
    assert result.content[0].components[0].healthcheck_day_logs[0].component_id == 100
    assert result.content[0].components[1].healthcheck_day_logs[0].overall_status is StatusType.DEGRADED


@pytest.mark.asyncio
async def test_get_all_products_skips_summary_query_when_there_are_no_components() -> None:
    product_repository = FakeProductRepository(
        initial_products=[Product(id=1, name="No Components", components=[], is_visible=True)]
    )
    log_repository = FakeLogRepository(precomputed_summary={})

    use_case = GetAllProductsUseCase(product_repository=product_repository, log_repository=log_repository)

    result = await use_case.execute(is_visible=True, page=1, page_size=10, summary_days=30)

    assert result.page_count == 1
    assert log_repository.bulk_calls == []
