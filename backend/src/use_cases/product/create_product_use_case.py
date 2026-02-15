from core.domain.product import Product
from core.port.product_repository import ProductRepository
from infra.web.routers.schemas.product import ProductCreateDTO


class CreateProductUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self.product_repository = product_repository

    async def execute(self, product: ProductCreateDTO) -> Product:
        product_entity = Product(
            id=None,
            name=product.name,
            description=product.description,
            is_visible=True,
        )

        return await self.product_repository.save(product_entity)
