from datetime import datetime, timedelta, timezone

import pytest

from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.product import Product
from core.domain.status_type import StatusType
from infra.adapter.postgres_component_repository import PostgresComponentRepository
from infra.adapter.postgres_log_repository import PostgresLogRepository
from infra.adapter.postgres_product_repository import PostgresProductRepository


async def _create_component(
    product_repository: PostgresProductRepository,
    component_repository: PostgresComponentRepository,
    *,
    name: str,
    health_url: str,
) -> int:
    product = await product_repository.save(Product(id=None, name=f"product-{name}", is_visible=True))

    component = await component_repository.save(
        Component(
            id=None,
            product_id=product.id or 0,
            name=name,
            type=ComponentType.BACKEND,
            monitoring_config=HealthcheckConfig(health_url=health_url),
            current_status=StatusType.OPERATIONAL,
        )
    )

    assert component.id is not None
    return component.id


@pytest.mark.asyncio
async def test_add_log_and_get_logs_ordered_by_checked_at_desc(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    log_repository = PostgresLogRepository(sqlite_session_factory)

    component_id = await _create_component(
        product_repository,
        component_repository,
        name="api",
        health_url="https://api.example.com/health",
    )

    now = datetime.now(timezone.utc)
    older = HealthcheckLog(
        component_id=component_id,
        checked_at=now - timedelta(minutes=5),
        is_successful=True,
        status_code=200,
        response_time_ms=150,
        status_before=StatusType.OPERATIONAL,
        status_after=StatusType.OPERATIONAL,
        error_message=None,
    )
    newer = HealthcheckLog(
        component_id=component_id,
        checked_at=now,
        is_successful=False,
        status_code=500,
        response_time_ms=300,
        status_before=StatusType.OPERATIONAL,
        status_after=StatusType.OUTAGE,
        error_message="boom",
    )

    await log_repository.add_log(older)
    await log_repository.add_log(newer)

    logs = await log_repository.get_logs(component_id=component_id, limit=1)

    assert len(logs) == 1
    assert logs[0].status_code == 500
    assert logs[0].error_message == "boom"


@pytest.mark.asyncio
async def test_get_last_n_day_summary_bulk_groups_by_component_and_day(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    log_repository = PostgresLogRepository(sqlite_session_factory)

    component_one_id = await _create_component(
        product_repository,
        component_repository,
        name="api-1",
        health_url="https://api-1.example.com/health",
    )
    component_two_id = await _create_component(
        product_repository,
        component_repository,
        name="api-2",
        health_url="https://api-2.example.com/health",
    )

    now = datetime.now(timezone.utc)

    await log_repository.add_log(
        HealthcheckLog(
            component_id=component_one_id,
            checked_at=now - timedelta(hours=1),
            is_successful=True,
            status_code=200,
            response_time_ms=100,
            status_before=StatusType.OPERATIONAL,
            status_after=StatusType.OPERATIONAL,
            error_message=None,
        )
    )
    await log_repository.add_log(
        HealthcheckLog(
            component_id=component_one_id,
            checked_at=now - timedelta(hours=2),
            is_successful=False,
            status_code=500,
            response_time_ms=300,
            status_before=StatusType.OPERATIONAL,
            status_after=StatusType.OUTAGE,
            error_message="error",
        )
    )
    await log_repository.add_log(
        HealthcheckLog(
            component_id=component_two_id,
            checked_at=now - timedelta(hours=1),
            is_successful=True,
            status_code=200,
            response_time_ms=50,
            status_before=StatusType.OPERATIONAL,
            status_after=StatusType.OPERATIONAL,
            error_message=None,
        )
    )

    summaries = await log_repository.get_last_n_day_summary_bulk(
        component_ids=[component_one_id, component_two_id, component_one_id],
        last_n_days=3,
    )

    assert component_one_id in summaries
    assert component_two_id in summaries

    first_summary = summaries[component_one_id][0]
    assert first_summary.total_checks == 2
    assert first_summary.successful_checks == 1
    assert first_summary.uptime == 50.0
    assert first_summary.avg_response_time == 200
    assert first_summary.max_response_time == 300
    assert first_summary.overall_status is StatusType.OUTAGE


@pytest.mark.asyncio
async def test_get_last_n_day_summary_returns_component_slice(sqlite_session_factory) -> None:
    product_repository = PostgresProductRepository(sqlite_session_factory)
    component_repository = PostgresComponentRepository(sqlite_session_factory)
    log_repository = PostgresLogRepository(sqlite_session_factory)

    component_id = await _create_component(
        product_repository,
        component_repository,
        name="api-single",
        health_url="https://api-single.example.com/health",
    )

    await log_repository.add_log(
        HealthcheckLog(
            component_id=component_id,
            checked_at=datetime.now(timezone.utc),
            is_successful=True,
            status_code=200,
            response_time_ms=90,
            status_before=StatusType.OPERATIONAL,
            status_after=StatusType.OPERATIONAL,
            error_message=None,
        )
    )

    summaries = await log_repository.get_last_n_day_summary(component_id=component_id, last_n_days=2)

    assert len(summaries) == 1
    assert summaries[0].component_id == component_id


@pytest.mark.asyncio
async def test_get_last_n_day_summary_bulk_returns_empty_for_no_component_ids(sqlite_session_factory) -> None:
    repository = PostgresLogRepository(sqlite_session_factory)

    assert await repository.get_last_n_day_summary_bulk(component_ids=[], last_n_days=5) == {}
