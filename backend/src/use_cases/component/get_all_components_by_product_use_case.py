from core.domain.component import Component
from core.domain.page import Page
from core.port.component_repository import ComponentRepository


class GetAllComponentsByProductUseCase:
    def __init__(self, component_repository: ComponentRepository) -> None:
        self.component_repository = component_repository

    async def execute(self, product_id: int, page: int, page_size: int) -> Page[Component]:
        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 10

        return await self.component_repository.find_all_by_product_id(
            product_id=product_id,
            page=page,
            page_size=page_size,
        )
