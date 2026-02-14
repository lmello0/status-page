from dataclasses import replace

from core.domain.product import Product
from core.exceptions.product_not_found_error import ProductNotFoundError
from core.port.product_repository import ProductRepository
from infra.web.routers.schemas.product import ProductUpdateDTO


class UpdateProductUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def execute(
        self,
        product_id: int,
        product_data: ProductUpdateDTO,
    ) -> Product:
        product = await self.product_repository.find_by_id(product_id)

        if not product:
            raise ProductNotFoundError

        updates = product_data.model_dump(exclude_none=True)

        updated_product = replace(product, **updates)

        updated_product = await self.product_repository.save(updated_product)

        return updated_product
