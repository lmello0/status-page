from dataclasses import replace

from core.domain.component import Component
from core.domain.page import Page
from core.domain.product import Product
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.port.log_repository import LogRepository
from core.port.product_repository import ProductRepository


class GetAllProductsUseCase:
    def __init__(
        self,
        product_repository: ProductRepository,
        log_repository: LogRepository,
    ):
        self.product_repository = product_repository
        self.log_repository = log_repository

    async def execute(self, is_visible: bool, page: int, page_size: int, summary_days: int = 100) -> Page[Product]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        products_page = await self.product_repository.find_all(is_visible=is_visible, page=page, page_size=page_size)
        component_ids = self._collect_component_ids(products_page)
        summary_by_component: dict[int, list[HealthcheckLogDaySummary]] = {}

        if component_ids:
            summary_by_component = await self.log_repository.get_last_n_day_summary_bulk(
                component_ids=component_ids,
                last_n_days=summary_days,
            )

        for product in products_page:
            product.components = [
                self._with_component_summary(component, summary_by_component)
                for component in product.components
            ]

        return products_page

    def _with_component_summary(
        self,
        component: Component,
        summary_by_component: dict[int, list[HealthcheckLogDaySummary]],
    ) -> Component:
        if component.id is None:
            return component

        return replace(component, healthcheck_day_logs=summary_by_component.get(component.id, []))

    def _collect_component_ids(self, products_page: Page[Product]) -> list[int]:
        component_ids = [
            component.id
            for product in products_page
            for component in product.components
            if component.id is not None
        ]

        return list(dict.fromkeys(component_ids))
