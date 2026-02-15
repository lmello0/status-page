from core.domain.status_type import StatusType
from core.exceptions.component_not_found_error import ComponentNotFoundError
from core.port.component_repository import ComponentRepository


class UpdateComponentStatusUseCase:
    def __init__(self, component_repository: ComponentRepository) -> None:
        self.component_repository = component_repository

    async def execute(self, component_id: int, status: StatusType):
        component = await self.component_repository.find_by_id(component_id)

        if not component:
            raise ComponentNotFoundError

        component.current_status = status

        await self.component_repository.save(component)
