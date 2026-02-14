from core.domain.component import Component
from core.domain.healthcheck_config import HealthcheckConfig
from core.port.component_repository import ComponentRepository
from infra.web.routers.schemas.component import ComponentCreateDTO


class CreateComponentUseCase:
    def __init__(self, component_repository: ComponentRepository) -> None:
        self.component_repository = component_repository

    async def execute(self, component: ComponentCreateDTO) -> Component:
        component_entity = Component(
            id=None,
            product_id=component.product_id,
            name=component.name,
            type=component.type,
            monitoring_config=HealthcheckConfig(
                health_url=component.monitoring_config.health_url,
                check_interval_seconds=component.monitoring_config.check_interval_seconds,
                timeout_seconds=component.monitoring_config.timeout_seconds,
                expected_status_code=component.monitoring_config.expected_status_code,
                max_response_time_ms=component.monitoring_config.max_response_time_ms,
                failures_before_outage=component.monitoring_config.failures_before_outage,
            ),
            current_status=None,
            is_active=True,
        )

        return await self.component_repository.save(component_entity)
