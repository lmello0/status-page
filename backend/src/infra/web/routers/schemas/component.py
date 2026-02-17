from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import Field, field_validator

from core.domain.component_type import ComponentType
from core.domain.status_type import StatusType
from infra.web.routers.schemas import CamelModel


class MonitoringConfigCreateDTO(CamelModel):
    health_url: str
    check_interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_code: int = 200
    max_response_time_ms: int = 5000
    failures_before_outage: int = 3

    @field_validator("health_url", mode="after")
    @classmethod
    def is_url_valid(cls, health_url: str):
        parsed = urlparse(health_url)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"Invalid URL: {health_url}")

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL must use http or https scheme: {health_url}")

        return health_url


class MonitoringConfigUpdateDTO(CamelModel):
    health_url: Optional[str] = None
    check_interval_seconds: Optional[int] = None
    timeout_seconds: Optional[int] = None
    expected_status_code: Optional[int] = None
    max_response_time_ms: Optional[int] = None
    failures_before_outage: Optional[int] = None

    @field_validator("health_url", mode="after")
    @classmethod
    def is_url_valid(cls, health_url: str):
        if health_url is not None:
            parsed = urlparse(health_url)
            if not all([parsed.scheme, parsed.netloc]):
                raise ValueError(f"Invalid URL: {health_url}")

            if parsed.scheme not in ("http", "https"):
                raise ValueError(f"URL must use http or https scheme: {health_url}")

        return health_url


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
    type: ComponentType
    monitoring_config: MonitoringConfigCreateDTO


class ComponentUpdateDTO(CamelModel):
    name: Optional[str] = None
    type: Optional[ComponentType] = None
    monitoring_config: Optional[MonitoringConfigUpdateDTO] = None


class HealthcheckLogDaySummaryResponseDTO(CamelModel):
    date: datetime
    total_checks: int
    successful_checks: int
    uptime: float
    avg_response_time: int
    max_response_time: int
    overall_status: StatusType


class ComponentResponseDTO(CamelModel):
    id: int
    product_id: int
    name: str
    type: ComponentType
    monitoring_config: MonitoringConfigResponseDTO
    current_status: Optional[StatusType] = None
    is_active: bool
    healthcheck_day_logs: list[HealthcheckLogDaySummaryResponseDTO] = Field(default_factory=list)
