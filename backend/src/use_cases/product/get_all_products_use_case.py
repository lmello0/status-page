import asyncio
from dataclasses import replace

from core.domain.component import Component
from core.domain.page import Page
from core.domain.product import Product
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

    async def execute(self, is_visible: bool, page: int, page_size: int) -> Page[Product]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        products_page = await self.product_repository.find_all(is_visible=is_visible, page=page, page_size=page_size)

        for product in products_page:
            product.components = await asyncio.gather(*[self._fetch_component_summary(c) for c in product.components])

        return products_page

    async def _fetch_component_summary(self, component: Component) -> Component:
        if not component.id:
            return component

        component_logs = await self.log_repository.get_last_n_day_summary(component.id, 100)

        return replace(component, healthcheck_day_logs=component_logs)
