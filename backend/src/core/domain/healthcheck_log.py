from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.domain.status_type import StatusType


@dataclass
class HealthcheckLog:
    component_id: int

    checked_at: datetime
    is_successful: bool
    status_code: Optional[int]
    response_time_ms: int

    status_before: StatusType
    status_after: StatusType
    error_message: Optional[str]
