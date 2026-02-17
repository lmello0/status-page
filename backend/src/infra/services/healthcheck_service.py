import logging
from datetime import datetime, timezone

import httpx
import structlog

from core.domain.component import Component
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.status_type import StatusType
from core.port.component_cache import ComponentCache
from core.port.scheduler import Scheduler
from use_cases.component.get_all_components_unpaginated_use_case import (
    GetAllComponentsUnpaginatedUseCase,
)
from use_cases.component.update_component_status_use_case import (
    UpdateComponentStatusUseCase,
)

logger = structlog.stdlib.get_logger(__name__)


class HealthcheckService:
    def __init__(
        self,
        sync_interval_seconds: int,
        scheduler: Scheduler,
        cache: ComponentCache,
        http_client: httpx.AsyncClient,
        get_components_use_case: GetAllComponentsUnpaginatedUseCase,
        update_component_use_case: UpdateComponentStatusUseCase,
    ):
        self.SYNC_INTERVAL_SECONDS = sync_interval_seconds
        self.scheduler = scheduler

        self.get_components_use_case = get_components_use_case
        self.update_component_use_case = update_component_use_case

        self.cache = cache
        self.http_client = http_client

        self._failure_counts: dict[int, int] = {}

    async def start(self):
        logger.info("Health check service started")

        self.scheduler.add_job(
            job_key="sync_components",
            func=self._sync_components_from_db,
            interval_seconds=self.SYNC_INTERVAL_SECONDS,
            job_name="Sync components from database",
        )

        await self._sync_components_from_db()

    async def _sync_components_from_db(self):
        logger.debug("Syncing components from database")

        try:
            components = await self.get_components_use_case.execute()

            cached_components = await self.cache.get_all()
            cached_ids = set(cached_components.keys())
            active_ids = {c.id for c in components if c.id is not None and c.is_active}

            removed_ids = cached_ids - active_ids
            for component_id in removed_ids:
                await self._unschedule_component(component_id)

            for component in components:
                if component.id is None:
                    logger.warning(
                        f"Skipping component without ID: {component.name}, product_id: {component.product_id}"
                    )
                    continue

                cached = await self.cache.get(component.id)

                needs_reschedule = (
                    cached is None
                    or cached.monitoring_config.check_interval_seconds
                    != component.monitoring_config.check_interval_seconds
                    or cached.monitoring_config.health_url != component.monitoring_config.health_url
                    or cached.monitoring_config.timeout_seconds != component.monitoring_config.timeout_seconds
                    or cached.monitoring_config.expected_status_code != component.monitoring_config.expected_status_code
                    or cached.monitoring_config.max_response_time_ms != component.monitoring_config.max_response_time_ms
                    or cached.monitoring_config.failures_before_outage
                    != component.monitoring_config.failures_before_outage
                )

                await self.cache.set(component)

                if needs_reschedule:
                    await self._schedule_component_health_check(component.id)

            logger.info(
                f"Synced {len(components)} active components "
                f"(added/updated: {len(active_ids - cached_ids)}, "
                f"removed: {len(removed_ids)})"
            )
        except Exception as e:
            logger.exception(f"Error syncing components from database: {e}")

    async def _schedule_component_health_check(self, component_id: int):
        component = await self.cache.get(component_id)

        if not component:
            logger.warning(f"Cannot schedule component {component_id} - not in cache")
            return

        job_key = f"health_check_component_{component.id}_product_{component.product_id}"

        self.scheduler.add_job(
            job_key=job_key,
            func=self._check_component_health,
            interval_seconds=component.monitoring_config.check_interval_seconds,
            args=(component_id,),
            job_name=f"Health check: {component.name}",
        )

        logger.info(
            f"Scheduled health check for component '{component.name}' "
            f"(ID: {component_id}, interval: {component.monitoring_config.check_interval_seconds}s)"
        )

    async def _unschedule_component(self, component_id: int):
        component = await self.cache.get(component_id)

        if not component:
            logger.warning(f"Cannot unschedule component {component_id} - not in cache")
            return

        job_key = f"health_check_component_{component.id}_product_{component.product_id}"

        if self.scheduler.remove_job(job_key):
            await self.cache.remove(component_id)
            self._failure_counts.pop(component_id, None)
            logger.info(f"Unscheduled health check for component {component_id}")

    async def _check_component_health(self, component_id: int):
        component = await self.cache.get(component_id)

        if not component:
            logger.warning(f"Component {component_id} not in cache, will be removed on next sync")
            return

        config = component.monitoring_config

        try:
            start_time = datetime.now(timezone.utc)

            response = await self.http_client.get(
                config.health_url,
                timeout=config.timeout_seconds,
            )

            end_time = datetime.now(timezone.utc)
            response_time_ms = (end_time - start_time).total_seconds() * 1_000

            status_ok = response.status_code == config.expected_status_code
            response_time_ok = response_time_ms <= config.max_response_time_ms

            is_healthy = status_ok and response_time_ok

            status_before = component.current_status or StatusType.OPERATIONAL

            if not is_healthy:
                self._failure_counts[component_id] = self._failure_counts.get(component_id, 0) + 1
                failure_count = self._failure_counts[component_id]

                if failure_count >= config.failures_before_outage:
                    new_status = StatusType.OUTAGE
                else:
                    new_status = StatusType.DEGRADED

            else:
                self._failure_counts[component_id] = 0
                new_status = StatusType.OPERATIONAL

            log = HealthcheckLog(
                component_id=component_id,
                checked_at=end_time,
                is_successful=is_healthy,
                status_code=response.status_code,
                response_time_ms=int(response_time_ms),
                status_before=status_before,
                status_after=new_status,
                error_message=response.text if not status_ok else None,
            )

            component.current_status = new_status
            component.healthcheck_day_logs.append(log)

            await self.update_component_use_case.execute(
                component_id=component_id,
                current_status=new_status,
                new_log=log,
            )

            log_level = logging.INFO if is_healthy else logging.WARNING
            logger.log(
                log_level,
                f"Health check '{component.name}': "
                f"status_code={response.status_code}, "
                f"response_time={response_time_ms:.2f}ms, "
                f"health={new_status.value}, "
                f"failures={self._failure_counts.get(component_id, 0)}",
            )

        except httpx.TimeoutException:
            logger.error(f"Health check timeout for '{component.name}' " f"(timeout: {config.timeout_seconds}s)")

            log = HealthcheckLog(
                component_id=component_id,
                checked_at=datetime.now(timezone.utc),
                is_successful=False,
                status_code=None,
                response_time_ms=config.timeout_seconds,
                status_before=component.current_status or StatusType.OPERATIONAL,
                status_after=StatusType.OUTAGE,
                error_message="Request timeout",
            )

            await self._handle_check_failure(component, StatusType.OUTAGE, log=log)

        except httpx.RequestError as e:
            logger.error(f"Health check failed for '{component.name}': {e}")

            log = HealthcheckLog(
                component_id=component_id,
                checked_at=datetime.now(timezone.utc),
                is_successful=False,
                status_code=None,
                response_time_ms=config.timeout_seconds,
                status_before=component.current_status or StatusType.OPERATIONAL,
                status_after=StatusType.OUTAGE,
                error_message=str(e),
            )

            await self._handle_check_failure(component, StatusType.OUTAGE, log=log)

        except Exception as e:
            logger.exception(f"Unexpected error checking '{component.name}': {e}")

            log = HealthcheckLog(
                component_id=component_id,
                checked_at=datetime.now(timezone.utc),
                is_successful=False,
                status_code=None,
                response_time_ms=config.timeout_seconds,
                status_before=component.current_status or StatusType.OPERATIONAL,
                status_after=StatusType.OUTAGE,
                error_message=f"Unexpected error: {str(e)}",
            )

            await self._handle_check_failure(component, StatusType.OUTAGE, log=log)

    async def _handle_check_failure(self, component: Component, status: StatusType, log: HealthcheckLog):
        if component.id is None:
            return

        self._failure_counts[component.id] = self._failure_counts.get(component.id, 0) + 1

        component.current_status = status
        component.healthcheck_day_logs.append(log)

        await self.update_component_use_case.execute(
            component_id=component.id,
            current_status=status,
            new_log=log,
        )

    async def trigger_immediate_check(self, component_id: int):
        await self._check_component_health(component_id)
