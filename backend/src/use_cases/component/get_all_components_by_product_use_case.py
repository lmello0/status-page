import asyncio
from dataclasses import replace

from core.domain.component import Component
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

    async def execute(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        component_page = await self.component_repository.find_all_by_product_id(
            product_id=product_id,
            page=page,
            page_size=page_size,
        )

        component_page.content = await asyncio.gather(*[self._fetch_component_summary(c) for c in component_page])

        return component_page

    async def _fetch_component_summary(self, component: Component) -> Component:
        if not component.id:
            return component

        component_logs = await self.log_repository.get_last_n_day_summary(component.id, 100)

        return replace(component, healthcheck_day_logs=component_logs)
