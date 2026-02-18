from copy import deepcopy
from dataclasses import replace
from datetime import datetime, time, timezone, timedelta
from math import ceil
from typing import Any

from core.domain.component import Component
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.page import Page
from core.domain.product import Product
from core.domain.status_type import StatusType
from core.exceptions.component_already_exists_error import ComponentAlreadyExistsError
from core.port.component_repository import ComponentRepository
from core.port.log_repository import LogRepository
from core.port.product_repository import ProductRepository
from core.port.scheduler import Scheduler


class FakeProductRepository(ProductRepository):
    def __init__(self, initial_products: list[Product] | None = None) -> None:
        self._products: dict[int, Product] = {}
        self._next_id = 1

        for product in initial_products or []:
            product_copy = deepcopy(product)
            if product_copy.id is None:
                product_copy.id = self._next_id
                self._next_id += 1
            self._products[product_copy.id] = product_copy
            self._next_id = max(self._next_id, product_copy.id + 1)

    async def save(self, product: Product) -> Product:
        product_copy = deepcopy(product)

        if product_copy.id is None or product_copy.id <= 0:
            product_copy.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, product_copy.id + 1)

        self._products[product_copy.id] = deepcopy(product_copy)
        return deepcopy(product_copy)

    async def find_by_id(self, product_id: int) -> Product | None:
        product = self._products.get(product_id)
        return deepcopy(product) if product is not None else None

    async def find_by_name(self, name: str) -> Product | None:
        for product in self._products.values():
            if product.name == name:
                return deepcopy(product)

        return None

    async def find_all(self, is_visible: bool, page: int, page_size: int) -> Page[Product]:
        filtered = [product for product in self._products.values() if product.is_visible is is_visible]
        ordered = sorted(filtered, key=lambda item: item.id or 0)

        total_elements = len(ordered)
        offset = (page - 1) * page_size
        content = [deepcopy(item) for item in ordered[offset : offset + page_size]]
        total_pages = (total_elements + page_size - 1) // page_size if total_elements > 0 else 0

        return Page(
            page_size=page_size,
            page_count=len(content),
            total_elements=total_elements,
            total_pages=total_pages,
            content=content,
        )

    async def delete(self, product_id: int) -> bool:
        self._products.pop(product_id, None)
        return True


class FakeComponentRepository(ComponentRepository):
    def __init__(self, initial_components: list[Component] | None = None, enforce_uniqueness: bool = True) -> None:
        self._components: dict[int, Component] = {}
        self._next_id = 1
        self._enforce_uniqueness = enforce_uniqueness

        for component in initial_components or []:
            component_copy = deepcopy(component)
            if component_copy.id is None:
                component_copy.id = self._next_id
                self._next_id += 1
            self._components[component_copy.id] = component_copy
            self._next_id = max(self._next_id, component_copy.id + 1)

    async def save(self, component: Component) -> Component:
        component_copy = deepcopy(component)

        if self._enforce_uniqueness:
            for existing in self._components.values():
                if existing.id == component_copy.id:
                    continue

                if existing.name == component_copy.name:
                    raise ComponentAlreadyExistsError("name", component_copy.name)

                if existing.monitoring_config.health_url == component_copy.monitoring_config.health_url:
                    raise ComponentAlreadyExistsError("health_url", component_copy.monitoring_config.health_url)

        if component_copy.id is None or component_copy.id <= 0:
            component_copy.id = self._next_id
            self._next_id += 1
        else:
            self._next_id = max(self._next_id, component_copy.id + 1)

        self._components[component_copy.id] = deepcopy(component_copy)

        return deepcopy(component_copy)

    async def find_all_without_pagination(self) -> list[Component]:
        components = [component for component in self._components.values() if component.is_active]
        ordered = sorted(components, key=lambda item: item.id or 0)

        return [deepcopy(component) for component in ordered]

    async def find_by_id(self, component_id: int) -> Component | None:
        component = self._components.get(component_id)
        return deepcopy(component) if component is not None else None

    async def find_all_by_product_id(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        filtered = [component for component in self._components.values() if component.product_id == product_id]
        ordered = sorted(filtered, key=lambda item: item.id or 0)

        total_elements = len(ordered)
        offset = (page - 1) * page_size
        content = [deepcopy(item) for item in ordered[offset : offset + page_size]]
        total_pages = (total_elements + page_size - 1) // page_size if total_elements > 0 else 0

        return Page(
            page_size=page_size,
            page_count=len(content),
            total_elements=total_elements,
            total_pages=total_pages,
            content=content,
        )

    async def delete(self, component_id: int) -> bool:
        self._components.pop(component_id, None)
        return True


class FakeLogRepository(LogRepository):
    def __init__(
        self,
        initial_logs: list[HealthcheckLog] | None = None,
        precomputed_summary: dict[int, list[HealthcheckLogDaySummary]] | None = None,
    ) -> None:
        self.logs: list[HealthcheckLog] = [deepcopy(log) for log in (initial_logs or [])]
        self.precomputed_summary = precomputed_summary
        self.bulk_calls: list[tuple[list[int], int]] = []

    async def add_log(self, log: HealthcheckLog) -> HealthcheckLog:
        log_copy = deepcopy(log)
        self.logs.append(log_copy)
        return deepcopy(log_copy)

    async def get_logs(self, component_id: int, limit: int) -> list[HealthcheckLog]:
        filtered = [log for log in self.logs if log.component_id == component_id]
        ordered = sorted(filtered, key=lambda item: item.checked_at, reverse=True)

        return [deepcopy(log) for log in ordered[:limit]]

    async def get_last_n_day_summary(self, component_id: int, last_n_days: int) -> list[HealthcheckLogDaySummary]:
        bulk_result = await self.get_last_n_day_summary_bulk([component_id], last_n_days)
        return bulk_result.get(component_id, [])

    async def get_last_n_day_summary_bulk(
        self,
        component_ids: list[int],
        last_n_days: int,
    ) -> dict[int, list[HealthcheckLogDaySummary]]:
        deduped_ids = list(dict.fromkeys(component_ids))
        self.bulk_calls.append((deduped_ids, last_n_days))

        if self.precomputed_summary is not None:
            return {
                component_id: [deepcopy(summary) for summary in self.precomputed_summary.get(component_id, [])]
                for component_id in deduped_ids
                if component_id in self.precomputed_summary
            }

        cutoff = datetime.now(timezone.utc) - timedelta(days=last_n_days)
        grouped: dict[tuple[int, datetime], list[HealthcheckLog]] = {}

        for log in self.logs:
            if log.component_id not in deduped_ids:
                continue

            if log.checked_at < cutoff:
                continue

            summary_date = datetime.combine(log.checked_at.date(), time.min, tzinfo=timezone.utc)
            grouped.setdefault((log.component_id, summary_date), []).append(log)

        summaries_by_component: dict[int, list[HealthcheckLogDaySummary]] = {}

        for (component_id, summary_date), component_logs in grouped.items():
            total_checks = len(component_logs)
            successful_checks = len([log for log in component_logs if log.is_successful])
            uptime = round((successful_checks / total_checks) * 100, 2)
            avg_response_time = ceil(sum(log.response_time_ms for log in component_logs) / total_checks)
            max_response_time = max(log.response_time_ms for log in component_logs)
            overall_status = max((log.status_after for log in component_logs), key=lambda item: item.severity)

            summary = HealthcheckLogDaySummary(
                component_id=component_id,
                date=summary_date,
                total_checks=total_checks,
                successful_checks=successful_checks,
                uptime=uptime,
                avg_response_time=avg_response_time,
                max_response_time=max_response_time,
                overall_status=overall_status,
            )

            summaries_by_component.setdefault(component_id, []).append(summary)

        for component_id in summaries_by_component:
            summaries_by_component[component_id] = sorted(
                summaries_by_component[component_id],
                key=lambda item: item.date,
                reverse=True,
            )

        return summaries_by_component


class FakeScheduler(Scheduler):
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.jobs: dict[str, dict[str, Any]] = {}

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def add_job(
        self,
        job_key: str,
        func,
        interval_seconds: int,
        args: tuple = (),
        kwargs: dict | None = None,
        job_name: str | None = None,
    ) -> None:
        self.jobs[job_key] = {
            "func": func,
            "interval_seconds": interval_seconds,
            "args": args,
            "kwargs": kwargs or {},
            "job_name": job_name or job_key,
        }

    def remove_job(self, job_key: str) -> bool:
        removed = job_key in self.jobs
        self.jobs.pop(job_key, None)
        return removed

    def has_job(self, job_key: str) -> bool:
        return job_key in self.jobs

    def get_all_jobs(self) -> list[str]:
        return list(self.jobs.keys())


def with_component_status(component: Component, status: StatusType) -> Component:
    return replace(component, current_status=status)
