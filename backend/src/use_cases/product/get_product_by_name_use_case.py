from core.domain.product import Product
from core.exceptions.product_not_found_error import ProductNotFoundError
from core.port.product_repository import ProductRepository


class GetProductByNameUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def execute(self, product_name: str) -> Product:
        product = await self.product_repository.find_by_name(product_name)

        if not product:
            raise ProductNotFoundError

        return product
