from dataclasses import dataclass, field
from typing import Optional

from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.status_type import StatusType


@dataclass
class Component:
    id: Optional[int]
    product_id: int

    name: str
    type: ComponentType
    monitoring_config: HealthcheckConfig
    current_status: Optional[StatusType] = None

    is_active: bool = True
    healthcheck_day_logs: list[HealthcheckLogDaySummary] = field(default_factory=list)
