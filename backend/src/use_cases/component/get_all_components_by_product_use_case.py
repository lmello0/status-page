from dataclasses import replace

from core.domain.component import Component
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.page import Page
from core.port.component_repository import ComponentRepository
from core.port.log_repository import LogRepository


class GetAllComponentsByProductUseCase:
    def __init__(
        self,
        component_repository: ComponentRepository,
        log_repository: LogRepository,
    ) -> None:
        self.component_repository = component_repository
        self.log_repository = log_repository

    async def execute(self, product_id: int, page: int, page_size: int, summary_days: int = 100) -> Page[Component]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        component_page = await self.component_repository.find_all_by_product_id(
            product_id=product_id,
            page=page,
            page_size=page_size,
        )
        component_ids = [component.id for component in component_page if component.id is not None]
        deduped_component_ids = list(dict.fromkeys(component_ids))
        summary_by_component: dict[int, list[HealthcheckLogDaySummary]] = {}

        if deduped_component_ids:
            summary_by_component = await self.log_repository.get_last_n_day_summary_bulk(
                component_ids=deduped_component_ids,
                last_n_days=summary_days,
            )

        component_page.content = [
            self._with_component_summary(component, summary_by_component)
            for component in component_page
        ]

        return component_page

    def _with_component_summary(
        self,
        component: Component,
        summary_by_component: dict[int, list[HealthcheckLogDaySummary]],
    ) -> Component:
        if component.id is None:
            return component

        return replace(component, healthcheck_day_logs=summary_by_component.get(component.id, []))
