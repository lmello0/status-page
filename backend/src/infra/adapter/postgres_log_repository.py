from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache

from sqlalchemy import Float, Integer, RowMapping, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.status_type import StatusType
from core.port.log_repository import LogRepository
from infra.db.models import HealthcheckLogModel
from infra.db.session import get_session_factory


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

        summary_date_expr = func.date(HealthcheckLogModel.checked_at).label("summary_date")
        total_checks_expr = func.count(HealthcheckLogModel.id).label("total_checks")
        successful_checks_expr = func.sum(case((HealthcheckLogModel.is_successful.is_(True), 1), else_=0)).label(
            "successful_checks"
        )
        uptime_expr = func.round(
            (cast(successful_checks_expr, Float) / cast(total_checks_expr, Float)) * 100.0, 2
        ).label("uptime")
        avg_response_time_expr = cast(func.avg(HealthcheckLogModel.response_time_ms) + 0.999_999, Integer).label(
            "avg_response_time"
        )
        max_response_time_expr = func.max(HealthcheckLogModel.response_time_ms).label("max_response_time")
        overall_status_expr = func.max(HealthcheckLogModel.status_after).label("overall_status")
        since = datetime.now(timezone.utc) - timedelta(days=last_n_days)

        statement = (
            select(
                HealthcheckLogModel.component_id.label("component_id"),
                summary_date_expr,
                total_checks_expr,
                successful_checks_expr,
                uptime_expr,
                avg_response_time_expr,
                max_response_time_expr,
                overall_status_expr,
            )
            .where(HealthcheckLogModel.component_id.in_(deduped_component_ids))
            .where(HealthcheckLogModel.checked_at >= since)
            .group_by(HealthcheckLogModel.component_id, summary_date_expr)
            .order_by(HealthcheckLogModel.component_id.asc(), summary_date_expr.desc())
        )

        async with self._session_factory() as session:
            rows = (await session.execute(statement)).mappings().all()

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
        raw_summary_date = row["summary_date"]

        summary_date: datetime
        if isinstance(raw_summary_date, datetime):
            summary_date = raw_summary_date
        elif isinstance(raw_summary_date, date):
            summary_date = datetime.combine(raw_summary_date, time.min, tzinfo=timezone.utc)
        else:
            parsed_date = date.fromisoformat(str(raw_summary_date))
            summary_date = datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)

        return HealthcheckLogDaySummary(
            component_id=int(row["component_id"]),
            date=summary_date,
            total_checks=int(row["total_checks"]),
            successful_checks=int(row["successful_checks"]),
            uptime=float(row["uptime"]),
            avg_response_time=int(row["avg_response_time"]),
            max_response_time=int(row["max_response_time"]),
            overall_status=StatusType(row["overall_status"]),
        )


@lru_cache
def get_log_repository() -> LogRepository:
    session_factory = get_session_factory()

    return PostgresLogRepository(session_factory=session_factory)
