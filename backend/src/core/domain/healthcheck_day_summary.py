from dataclasses import dataclass
from datetime import datetime

from core.domain.status_type import StatusType


@dataclass
class HealthcheckLogDaySummary:
    component_id: int
    date: datetime
    total_checks: int
    successful_checks: int
    uptime: float
    avg_response_time: int
    max_response_time: int
    overall_status: StatusType
