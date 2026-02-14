from core.domain.product import Product
from core.exceptions.product_not_found_error import ProductNotFoundError
from core.port.product_repository import ProductRepository


class GetProductByIdUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def execute(self, product_id: int) -> Product:
        product = await self.product_repository.find_by_id(product_id)

        if not product:
            raise ProductNotFoundError

        return product
