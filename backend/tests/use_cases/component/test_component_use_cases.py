from datetime import datetime, timezone

import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.status_type import StatusType
from core.exceptions.component_not_found_error import ComponentNotFoundError
from infra.web.routers.schemas.component import ComponentCreateDTO, ComponentUpdateDTO, MonitoringConfigCreateDTO
from tests.support.fakes import FakeComponentRepository, FakeLogRepository
from use_cases.component.create_component_use_case import CreateComponentUseCase
from use_cases.component.delete_component_use_case import DeleteComponentUseCase
from use_cases.component.get_all_components_by_product_use_case import GetAllComponentsByProductUseCase
from use_cases.component.get_all_components_unpaginated_use_case import GetAllComponentsUnpaginatedUseCase
from use_cases.component.update_component_status_use_case import UpdateComponentStatusUseCase
from use_cases.component.update_component_use_case import UpdateComponentUseCase


class CountingComponentRepository(FakeComponentRepository):
    def __init__(self, initial_components: list[Component] | None = None) -> None:
        super().__init__(initial_components=initial_components)
        self.save_calls = 0

    async def save(self, component: Component) -> Component:
        self.save_calls += 1
        return await super().save(component)


def _component(component_id: int, product_id: int, name: str) -> Component:
    return Component(
        id=component_id,
        product_id=product_id,
        name=name,
        type=ComponentType.BACKEND,
        monitoring_config=HealthcheckConfig(health_url=f"https://{name}.example.com/health"),
        current_status=StatusType.OPERATIONAL,
    )


@pytest.mark.asyncio
async def test_create_component_use_case_maps_monitoring_config() -> None:
    repository = FakeComponentRepository()
    use_case = CreateComponentUseCase(repository)

    created = await use_case.execute(
        ComponentCreateDTO(
            product_id=5,
            name="API",
            type=ComponentType.BACKEND,
            monitoring_config=MonitoringConfigCreateDTO(
                health_url="https://api.example.com/health",
                check_interval_seconds=30,
                timeout_seconds=4,
                expected_status_code=204,
                max_response_time_ms=250,
                failures_before_outage=2,
            ),
        )
    )

    assert created.id is not None
    assert created.product_id == 5
    assert created.monitoring_config.expected_status_code == 204


@pytest.mark.asyncio
async def test_get_all_components_unpaginated_returns_active_components_only() -> None:
    repository = FakeComponentRepository(
        initial_components=[
            _component(1, 10, "one"),
            _component(2, 10, "two"),
        ]
    )
    disabled = _component(3, 10, "three")
    disabled.is_active = False
    await repository.save(disabled)

    use_case = GetAllComponentsUnpaginatedUseCase(repository)
    result = await use_case.execute()

    assert [component.id for component in result] == [1, 2]


@pytest.mark.asyncio
async def test_get_all_components_by_product_enriches_day_logs_and_normalizes_pagination() -> None:
    repository = FakeComponentRepository(
        initial_components=[
            _component(10, 99, "api"),
            _component(20, 99, "db"),
        ]
    )
    summaries = {
        10: [
            HealthcheckLogDaySummary(
                component_id=10,
                date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                total_checks=2,
                successful_checks=2,
                uptime=100.0,
                avg_response_time=10,
                max_response_time=15,
                overall_status=StatusType.OPERATIONAL,
            )
        ]
    }
    log_repository = FakeLogRepository(precomputed_summary=summaries)

    use_case = GetAllComponentsByProductUseCase(repository, log_repository)
    result = await use_case.execute(product_id=99, page=0, page_size=0, summary_days=14)

    assert result.page_size == 10
    assert result.page_count == 2
    assert log_repository.bulk_calls == [([10, 20], 14)]
    assert result.content[0].healthcheck_day_logs[0].component_id == 10
    assert result.content[1].healthcheck_day_logs == []


@pytest.mark.asyncio
async def test_update_component_raises_when_component_does_not_exist() -> None:
    repository = FakeComponentRepository()
    use_case = UpdateComponentUseCase(repository)

    with pytest.raises(ComponentNotFoundError):
        await use_case.execute(
            component_id=999,
            component_data=ComponentUpdateDTO(name="new"),
        )


@pytest.mark.asyncio
async def test_update_component_updates_scalar_fields() -> None:
    repository = FakeComponentRepository(initial_components=[_component(7, 1, "api")])
    use_case = UpdateComponentUseCase(repository)

    updated = await use_case.execute(
        component_id=7,
        component_data=ComponentUpdateDTO(name="api-v2"),
    )

    assert updated.name == "api-v2"


@pytest.mark.asyncio
async def test_update_component_status_updates_component_and_adds_log() -> None:
    component_repository = CountingComponentRepository(initial_components=[_component(42, 10, "payments")])
    log_repository = FakeLogRepository()
    use_case = UpdateComponentStatusUseCase(component_repository, log_repository)

    log = HealthcheckLog(
        component_id=42,
        checked_at=datetime.now(timezone.utc),
        is_successful=False,
        status_code=500,
        response_time_ms=600,
        status_before=StatusType.OPERATIONAL,
        status_after=StatusType.DEGRADED,
        error_message="slow",
    )

    result = await use_case.execute(component_id=42, current_status=StatusType.DEGRADED, new_log=log)

    assert component_repository.save_calls == 2
    assert result.current_status is StatusType.DEGRADED
    assert len(log_repository.logs) == 1
    assert log_repository.logs[0].component_id == 42


@pytest.mark.asyncio
async def test_update_component_status_raises_when_component_is_missing() -> None:
    use_case = UpdateComponentStatusUseCase(FakeComponentRepository(), FakeLogRepository())

    with pytest.raises(ComponentNotFoundError):
        await use_case.execute(
            component_id=123,
            current_status=StatusType.OUTAGE,
            new_log=HealthcheckLog(
                component_id=123,
                checked_at=datetime.now(timezone.utc),
                is_successful=False,
                status_code=None,
                response_time_ms=30,
                status_before=StatusType.OPERATIONAL,
                status_after=StatusType.OUTAGE,
                error_message="boom",
            ),
        )


@pytest.mark.asyncio
async def test_delete_component_use_case_returns_repository_result() -> None:
    repository = FakeComponentRepository(initial_components=[_component(1, 1, "api")])
    use_case = DeleteComponentUseCase(repository)

    assert await use_case.execute(1) is True
