from dataclasses import replace

from core.domain.component import Component
from core.exceptions.component_not_found_error import ComponentNotFoundError
from core.port.component_repository import ComponentRepository
from infra.web.routers.schemas.component import ComponentUpdateDTO


class UpdateComponentUseCase:
    def __init__(self, component_repository: ComponentRepository) -> None:
        self.component_repository = component_repository

    async def execute(
        self,
        component_id: int,
        component_data: ComponentUpdateDTO,
    ) -> Component:
        component = await self.component_repository.find_by_id(component_id)

        if not component:
            raise ComponentNotFoundError

        updates = component_data.model_dump(exclude_none=True)

        updated_component = replace(component, **updates)

        updated_component = await self.component_repository.save(updated_component)

        return updated_component
