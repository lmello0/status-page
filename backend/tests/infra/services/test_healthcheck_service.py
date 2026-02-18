from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timezone

import httpx
import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.status_type import StatusType
from infra.adapter.dict_component_cache import DictComponentCache
from infra.services.healthcheck_service import HealthcheckService
from tests.support.fakes import FakeComponentRepository, FakeLogRepository, FakeScheduler
from use_cases.component.get_all_components_unpaginated_use_case import GetAllComponentsUnpaginatedUseCase
from use_cases.component.update_component_status_use_case import UpdateComponentStatusUseCase


def _component(
    component_id: int,
    *,
    product_id: int = 1,
    check_interval_seconds: int = 30,
    timeout_seconds: int = 2,
    expected_status_code: int = 200,
    max_response_time_ms: int = 1_000,
    failures_before_outage: int = 2,
    is_active: bool = True,
    current_status: StatusType | None = StatusType.OPERATIONAL,
) -> Component:
    return Component(
        id=component_id,
        product_id=product_id,
        name=f"component-{component_id}",
        type=ComponentType.BACKEND,
        monitoring_config=HealthcheckConfig(
            health_url=f"https://service-{component_id}.example.com/health",
            check_interval_seconds=check_interval_seconds,
            timeout_seconds=timeout_seconds,
            expected_status_code=expected_status_code,
            max_response_time_ms=max_response_time_ms,
            failures_before_outage=failures_before_outage,
        ),
        current_status=current_status,
        is_active=is_active,
    )


@pytest.fixture
async def service_factory() -> AsyncGenerator:
    clients: list[httpx.AsyncClient] = []

    async def _factory(
        components: list[Component],
        handler: Callable[[httpx.Request], httpx.Response],
    ):
        scheduler = FakeScheduler()
        cache = DictComponentCache()
        component_repository = FakeComponentRepository(initial_components=components)
        log_repository = FakeLogRepository()
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        clients.append(http_client)

        service = HealthcheckService(
            sync_interval_seconds=10,
            scheduler=scheduler,
            cache=cache,
            http_client=http_client,
            get_components_use_case=GetAllComponentsUnpaginatedUseCase(component_repository),
            update_component_use_case=UpdateComponentStatusUseCase(component_repository, log_repository),
        )

        return service, component_repository, log_repository, scheduler, cache

    try:
        yield _factory
    finally:
        for client in clients:
            await client.aclose()


@pytest.mark.asyncio
async def test_start_registers_sync_job_and_schedules_component_checks(service_factory) -> None:
    component = _component(1, product_id=99, check_interval_seconds=45)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    service, _, _, scheduler, cache = await service_factory([component], handler)

    await service.start()

    assert scheduler.has_job("sync_components")
    assert scheduler.has_job("health_check_component_1_product_99")
    cached_component = await cache.get(1)
    assert cached_component is not None


@pytest.mark.asyncio
async def test_sync_reschedules_when_monitoring_config_changes(service_factory) -> None:
    initial_component = _component(1, product_id=1, check_interval_seconds=15)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    service, component_repo, _, scheduler, _ = await service_factory([initial_component], handler)

    await service.start()
    assert scheduler.jobs["health_check_component_1_product_1"]["interval_seconds"] == 15

    updated_component = _component(1, product_id=1, check_interval_seconds=60)
    await component_repo.save(updated_component)

    await service._sync_components_from_db()

    assert scheduler.jobs["health_check_component_1_product_1"]["interval_seconds"] == 60


@pytest.mark.asyncio
async def test_sync_removes_jobs_for_deactivated_components(service_factory) -> None:
    component = _component(1, product_id=3, check_interval_seconds=20)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    service, component_repo, _, scheduler, cache = await service_factory([component], handler)

    await service.start()
    assert scheduler.has_job("health_check_component_1_product_3")

    inactive_component = _component(1, product_id=3, is_active=False)
    await component_repo.save(inactive_component)

    await service._sync_components_from_db()

    assert not scheduler.has_job("health_check_component_1_product_3")
    assert await cache.get(1) is None


@pytest.mark.asyncio
async def test_check_component_health_marks_operational_and_resets_failure_count(service_factory) -> None:
    component = _component(5, current_status=StatusType.DEGRADED)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="healthy")

    service, component_repo, log_repo, _, cache = await service_factory([component], handler)
    await cache.set(component)
    service._failure_counts[5] = 3

    await service._check_component_health(5)

    persisted = await component_repo.find_by_id(5)
    assert persisted is not None
    assert persisted.current_status is StatusType.OPERATIONAL
    assert service._failure_counts[5] == 0
    assert len(log_repo.logs) == 1
    assert log_repo.logs[0].is_successful is True


@pytest.mark.asyncio
async def test_check_component_health_escalates_from_degraded_to_outage_after_threshold(service_factory) -> None:
    component = _component(7, failures_before_outage=2)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="error")

    service, component_repo, log_repo, _, cache = await service_factory([component], handler)
    await cache.set(component)

    await service._check_component_health(7)
    first = await component_repo.find_by_id(7)
    assert first is not None
    assert first.current_status is StatusType.DEGRADED

    await service._check_component_health(7)
    second = await component_repo.find_by_id(7)
    assert second is not None
    assert second.current_status is StatusType.OUTAGE
    assert [entry.status_after for entry in log_repo.logs] == [StatusType.DEGRADED, StatusType.OUTAGE]


@pytest.mark.asyncio
async def test_timeout_marks_component_outage_and_records_timeout_error(service_factory) -> None:
    component = _component(8, timeout_seconds=3)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    service, component_repo, log_repo, _, cache = await service_factory([component], handler)
    await cache.set(component)

    await service._check_component_health(8)

    persisted = await component_repo.find_by_id(8)
    assert persisted is not None
    assert persisted.current_status is StatusType.OUTAGE
    assert log_repo.logs[0].error_message == "Request timeout"
    assert log_repo.logs[0].status_after is StatusType.OUTAGE


@pytest.mark.asyncio
async def test_request_error_marks_component_outage_and_records_error(service_factory) -> None:
    component = _component(9)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("cannot connect", request=request)

    service, component_repo, log_repo, _, cache = await service_factory([component], handler)
    await cache.set(component)

    await service._check_component_health(9)

    persisted = await component_repo.find_by_id(9)
    assert persisted is not None
    assert persisted.current_status is StatusType.OUTAGE
    assert "cannot connect" in (log_repo.logs[0].error_message or "")


@pytest.mark.asyncio
async def test_trigger_immediate_check_runs_check_once(service_factory) -> None:
    component = _component(11)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    service, _, log_repo, _, cache = await service_factory([component], handler)
    await cache.set(component)

    await service.trigger_immediate_check(11)

    assert len(log_repo.logs) == 1
    assert log_repo.logs[0].checked_at <= datetime.now(timezone.utc)
