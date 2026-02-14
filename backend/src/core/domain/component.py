from dataclasses import dataclass, field
from typing import Optional

from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.status_type import StatusType


@dataclass
class Component:
    id: int
    product_id: int

    name: str
    type: str
    current_status: StatusType = StatusType.OPERATIONAL
    parent_id: Optional[int] = None

    subcomponents: list["Component"] = field(default_factory=list)

    monitoring_config: Optional[HealthcheckConfig] = None

    is_active: bool = True

    def is_leaf(self) -> bool:
        return self.monitoring_config is not None

    def get_aggregated_status(self) -> StatusType:
        if self.is_leaf() or not self.subcomponents:
            return self.current_status

        worst_status = self.current_status
        for child in self.subcomponents:
            child_status = child.get_aggregated_status()
            if child_status.severity > worst_status.severity:
                worst_status = child_status

        return worst_status
