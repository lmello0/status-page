import asyncio
from dataclasses import replace

from core.domain.component import Component
from core.domain.healthcheck_log import HealthcheckLog
from core.domain.status_type import StatusType
from core.exceptions.component_not_found_error import ComponentNotFoundError
from core.port.component_repository import ComponentRepository
from core.port.log_repository import LogRepository


class UpdateComponentStatusUseCase:
    def __init__(self, component_repository: ComponentRepository, log_repository: LogRepository) -> None:
        self.component_repository = component_repository
        self.log_repository = log_repository

    async def execute(
        self,
        component_id: int,
        current_status: StatusType,
        new_log: HealthcheckLog,
    ) -> Component:
        component = await self.component_repository.find_by_id(component_id)

        if not component:
            raise ComponentNotFoundError

        updated_component = replace(component, current_status=current_status)

        await asyncio.gather(
            *[
                self.component_repository.save(updated_component),
                self.log_repository.add_log(new_log),
            ]
        )

        return await self.component_repository.save(updated_component)
