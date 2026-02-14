from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from core.domain.component import Component
from core.domain.status_type import StatusType


@dataclass
class Product:
    id: Optional[int]

    name: str
    description: Optional[str] = None

    is_visible: bool = True

    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    components: list[Component] = field(default_factory=list)

    def get_overall_status(self) -> StatusType:
        if not self.components:
            return StatusType.OPERATIONAL

        statuses = [comp.current_status for comp in self.components]
        return max(statuses, key=lambda s: s.severity)
