from core.port.component_repository import ComponentRepository


class DeleteComponentUseCase:
    def __init__(self, component_repository: ComponentRepository) -> None:
        self.component_repository = component_repository

    async def execute(self, component_id: int) -> bool:
        return await self.component_repository.delete(component_id)
