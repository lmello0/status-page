from core.domain.page import Page
from core.domain.product import Product
from core.port.product_repository import ProductRepository


class GetAllProductsUseCase:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    async def execute(self, is_visible: bool, page: int, page_size: int) -> Page[Product]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        return await self.product_repository.find_all(is_visible=is_visible, page=page, page_size=page_size)
