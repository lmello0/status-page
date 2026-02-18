from datetime import datetime, timezone

import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.product import Product
from core.domain.status_type import StatusType
from infra.adapter.postgres_component_repository import PostgresComponentRepository
from infra.adapter.postgres_product_repository import PostgresProductRepository


@pytest.mark.asyncio
async def test_save_and_find_product_by_id(sqlite_session_factory) -> None:
    repository = PostgresProductRepository(sqlite_session_factory)

    saved = await repository.save(Product(id=None, name="Payments", description="API", is_visible=True))
    found = await repository.find_by_id(saved.id or 0)

    assert saved.id is not None
    assert found is not None
    assert found.name == "Payments"
    assert found.description == "API"


@pytest.mark.asyncio
async def test_save_updates_existing_product(sqlite_session_factory) -> None:
    repository = PostgresProductRepository(sqlite_session_factory)

    saved = await repository.save(Product(id=None, name="Payments", description="Old", is_visible=True))
    updated = await repository.save(Product(id=saved.id, name="Payments v2", description="New", is_visible=False))

    assert updated.id == saved.id
    assert updated.name == "Payments v2"
    assert updated.is_visible is False


@pytest.mark.asyncio
async def test_find_by_name_returns_none_when_missing(sqlite_session_factory) -> None:
    repository = PostgresProductRepository(sqlite_session_factory)

    assert await repository.find_by_name("missing") is None


@pytest.mark.asyncio
async def test_find_all_paginates_and_maps_components(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)

    first = await product_repository.save(Product(id=None, name="A", is_visible=True))
    second = await product_repository.save(Product(id=None, name="B", is_visible=True))
    await product_repository.save(Product(id=None, name="Hidden", is_visible=False))

    await component_repository.save(
        Component(
            id=None,
            product_id=first.id or 0,
            name="component-a",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://a.example.com/health"),
            current_status=StatusType.OPERATIONAL,
        )
    )

    await component_repository.save(
        Component(
            id=None,
            product_id=first.id or 0,
            name="component-b",
            type=ComponentType.FRONTEND,
            monitoring_config=HealthcheckConfig(health_url="https://b.example.com/health"),
            current_status=StatusType.DEGRADED,
        )
    )

    page = await product_repository.find_all(is_visible=True, page=1, page_size=1)

    assert page.total_elements == 2
    assert page.total_pages == 2
    assert page.page_count == 1
    assert page.content[0].id == first.id
    assert len(page.content[0].components) == 2

    second_page = await product_repository.find_all(is_visible=True, page=2, page_size=1)
    assert second_page.content[0].id == second.id


@pytest.mark.asyncio
async def test_delete_product_removes_row(sqlite_session_factory) -> None:
    repository = PostgresProductRepository(sqlite_session_factory)
    saved = await repository.save(Product(id=None, name="DeleteMe", is_visible=True))

    deleted = await repository.delete(saved.id or 0)
    found = await repository.find_by_id(saved.id or 0)

    assert deleted is True
    assert found is None
