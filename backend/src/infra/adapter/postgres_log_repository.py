from functools import lru_cache

from sqlalchemy import RowMapping, bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.status_type import StatusType
from core.port.log_repository import LogRepository
from infra.db.models import HealthcheckLogModel
from infra.db.session import get_session_factory

SUMMARY_BULK_QUERY = """
    SELECT
        component_id,
        checked_at::date                                                           as summary_date,
        count(*)                                                                   as total_checks,
        count(*) filter (where is_successful)                                      as successful_checks,
        round((count(*) filter(where is_successful) / count(*)::numeric) * 100, 2) as uptime,
        ceil(avg(response_time_ms))                                                as avg_response_time,
        max(response_time_ms)                                                      as max_response_time,
        max(status_after)                                                          as overall_status
    from health_checks
    where
        component_id IN :component_ids
        and checked_at >= current_date - cast(:last_n_days as integer)
    group by component_id, checked_at::date
    order by component_id ASC, summary_date DESC
"""


class PostgresLogRepository(LogRepository):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    async def add_log(self, log: HealthcheckLog) -> HealthcheckLog:
        async with self._session_factory() as session:
            model = HealthcheckLogModel(
                component_id=log.component_id,
                checked_at=log.checked_at,
                is_successful=log.is_successful,
                status_code=log.status_code,
                response_time_ms=log.response_time_ms,
                status_before=log.status_before,
                status_after=log.status_after,
                error_message=log.error_message,
            )

            session.add(model)

            await session.commit()
            await session.refresh(model)

            return self._to_domain(model)

    async def get_logs(self, component_id: int, limit: int) -> list[HealthcheckLog]:
        async with self._session_factory() as session:
            statement = (
                select(HealthcheckLogModel)
                .where(HealthcheckLogModel.component_id == component_id)
                .order_by(HealthcheckLogModel.checked_at.desc())
                .limit(limit)
            )
            models = (await session.execute(statement)).scalars().all()

            return [self._to_domain(model) for model in models]

    async def get_last_n_day_summary(self, component_id: int, last_n_days: int) -> list[HealthcheckLogDaySummary]:
        bulk_result = await self.get_last_n_day_summary_bulk(
            component_ids=[component_id],
            last_n_days=last_n_days,
        )

        return bulk_result.get(component_id, [])

    async def get_last_n_day_summary_bulk(
        self,
        component_ids: list[int],
        last_n_days: int,
    ) -> dict[int, list[HealthcheckLogDaySummary]]:
        deduped_component_ids = list(dict.fromkeys(component_ids))

        if not deduped_component_ids:
            return {}

        async with self._session_factory() as session:
            statement = text(SUMMARY_BULK_QUERY).bindparams(bindparam("component_ids", expanding=True))

            rows = (
                (
                    await session.execute(
                        statement,
                        {
                            "component_ids": deduped_component_ids,
                            "last_n_days": last_n_days,
                        },
                    )
                )
                .mappings()
                .all()
            )

            summaries_by_component: dict[int, list[HealthcheckLogDaySummary]] = {}

            for row in rows:
                component_id = int(row["component_id"])
                summaries_by_component.setdefault(component_id, []).append(self._to_day_summary(row))

            return summaries_by_component

    def _to_domain(self, model: HealthcheckLogModel) -> HealthcheckLog:
        return HealthcheckLog(
            component_id=model.component_id,
            checked_at=model.checked_at,
            is_successful=model.is_successful,
            status_code=model.status_code,
            response_time_ms=model.response_time_ms,
            status_before=model.status_before,
            status_after=model.status_after,
            error_message=model.error_message,
        )

    def _to_day_summary(self, row: RowMapping) -> HealthcheckLogDaySummary:
        return HealthcheckLogDaySummary(
            component_id=int(row["component_id"]),
            date=row["summary_date"],
            total_checks=int(row["total_checks"]),
            successful_checks=int(row["successful_checks"]),
            uptime=float(row["uptime"]),
            avg_response_time=int(row["avg_response_time"]),
            max_response_time=int(row["max_response_time"]),
            overall_status=StatusType(str(row["overall_status"])),
        )


@lru_cache
def get_log_repository() -> LogRepository:
    session_factory = get_session_factory()

    return PostgresLogRepository(session_factory=session_factory)
