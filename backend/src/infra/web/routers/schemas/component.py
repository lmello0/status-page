from typing import Optional

from core.domain.status_type import StatusType
from infra.web.routers.schemas import CamelModel


class MonitoringConfigCreateDTO(CamelModel):
    health_url: str
    check_interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_code: int = 200
    max_response_time_ms: int = 5000
    failures_before_outage: int = 3


class MonitoringConfigUpdateDTO(CamelModel):
    health_url: Optional[str] = None
    check_interval_seconds: Optional[int] = None
    timeout_seconds: Optional[int] = None
    expected_status_code: Optional[int] = None
    max_response_time_ms: Optional[int] = None
    failures_before_outage: Optional[int] = None


class MonitoringConfigResponseDTO(CamelModel):
    health_url: str
    check_interval_seconds: int
    timeout_seconds: int
    expected_status_code: int
    max_response_time_ms: int
    failures_before_outage: int


class ComponentCreateDTO(CamelModel):
    product_id: int
    name: str
    type: str
    monitoring_config: MonitoringConfigCreateDTO


class ComponentUpdateDTO(CamelModel):
    name: Optional[str] = None
    type: Optional[str] = None
    monitoring_config: Optional[MonitoringConfigUpdateDTO] = None
    current_status: Optional[StatusType] = None
    is_active: Optional[bool] = None


class ComponentResponseDTO(CamelModel):
    id: int
    product_id: int
    name: str
    type: str
    monitoring_config: MonitoringConfigResponseDTO
    current_status: StatusType
    parent_id: Optional[int] = None
    is_active: bool
