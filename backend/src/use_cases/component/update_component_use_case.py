from dataclasses import replace

from core.domain.component import Component
from core.domain.healthcheck_config import HealthcheckConfig
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

        updates = {}
        if component_data.name is not None:
            updates["name"] = component_data.name

        if component_data.type is not None:
            updates["type"] = component_data.type

        if component_data.monitoring_config is not None:
            updates["monitoring_config"] = HealthcheckConfig(
                **component_data.monitoring_config.model_dump(exclude_none=True)
            )

        updated_component = replace(component, **updates)

        updated_component = await self.component_repository.save(updated_component)

        return updated_component
