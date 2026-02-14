from core.port.product_repository import ProductRepository


class DeleteProductUseCase:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    async def execute(self, product_id: int) -> bool:
        return await self.product_repository.delete(product_id)
