import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.product import Product
from core.domain.status_type import StatusType
from core.exceptions.component_already_exists_error import ComponentAlreadyExistsError
from infra.adapter.postgres_component_repository import PostgresComponentRepository
from infra.adapter.postgres_product_repository import PostgresProductRepository


async def _create_product(product_repository: PostgresProductRepository, name: str = "Product") -> int:
    created = await product_repository.save(Product(id=None, name=name, is_visible=True))
    assert created.id is not None
    return created.id


@pytest.mark.asyncio
async def test_save_and_find_component_by_id(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    saved = await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="payments-api",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://payments.example.com/health"),
            current_status=StatusType.OPERATIONAL,
        )
    )

    found = await component_repository.find_by_id(saved.id or 0)

    assert saved.id is not None
    assert found is not None
    assert found.name == "payments-api"


@pytest.mark.asyncio
async def test_save_component_duplicate_name_raises_domain_error(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="shared-name",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://a.example.com/health"),
        )
    )

    with pytest.raises(ComponentAlreadyExistsError) as exc_info:
        await component_repository.save(
            Component(
                id=None,
                product_id=product_id,
                name="shared-name",
                type=ComponentType.FRONTEND,
                monitoring_config=HealthcheckConfig(health_url="https://b.example.com/health"),
            )
        )

    assert exc_info.value.field == "name"


@pytest.mark.asyncio
async def test_save_component_duplicate_health_url_raises_domain_error(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="api-one",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://duplicate.example.com/health"),
        )
    )

    with pytest.raises(ComponentAlreadyExistsError) as exc_info:
        await component_repository.save(
            Component(
                id=None,
                product_id=product_id,
                name="api-two",
                type=ComponentType.BACKEND,
                monitoring_config=HealthcheckConfig(health_url="https://duplicate.example.com/health"),
            )
        )

    assert exc_info.value.field == "health_url"


@pytest.mark.asyncio
async def test_find_all_by_product_id_paginates(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    for idx in range(1, 4):
        await component_repository.save(
            Component(
                id=None,
                product_id=product_id,
                name=f"component-{idx}",
                type=ComponentType.BACKEND,
                monitoring_config=HealthcheckConfig(health_url=f"https://{idx}.example.com/health"),
            )
        )

    first_page = await component_repository.find_all_by_product_id(product_id, page=1, page_size=2)
    second_page = await component_repository.find_all_by_product_id(product_id, page=2, page_size=2)

    assert first_page.total_elements == 3
    assert first_page.total_pages == 2
    assert [item.name for item in first_page.content] == ["component-1", "component-2"]
    assert [item.name for item in second_page.content] == ["component-3"]


@pytest.mark.asyncio
async def test_find_all_without_pagination_returns_only_active_components(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    active = await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="active",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://active.example.com/health"),
            is_active=True,
        )
    )

    await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="inactive",
            type=ComponentType.FRONTEND,
            monitoring_config=HealthcheckConfig(health_url="https://inactive.example.com/health"),
            is_active=False,
        )
    )

    found = await component_repository.find_all_without_pagination()

    assert [component.id for component in found] == [active.id]


@pytest.mark.asyncio
async def test_delete_component_removes_row(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    product_id = await _create_product(product_repository)

    saved = await component_repository.save(
        Component(
            id=None,
            product_id=product_id,
            name="to-delete",
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url="https://delete.example.com/health"),
        )
    )

    deleted = await component_repository.delete(saved.id or 0)
    found = await component_repository.find_by_id(saved.id or 0)

    assert deleted is True
    assert found is None
