from core.domain.component import Component
from core.port.component_repository import ComponentRepository


class GetAllComponentsUnpaginatedUseCase:
    def __init__(self, component_repository: ComponentRepository):
        self.component_repository = component_repository

    async def execute(self) -> list[Component]:
        return await self.component_repository.find_all_without_pagination()
