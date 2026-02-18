import pytest
from pydantic import ValidationError

from core.domain.component_type import ComponentType
from infra.web.routers.schemas.component import (
    ComponentCreateDTO,
    MonitoringConfigCreateDTO,
    MonitoringConfigUpdateDTO,
)


def test_monitoring_config_create_rejects_invalid_url() -> None:
    with pytest.raises(ValidationError, match="Invalid URL"):
        MonitoringConfigCreateDTO(health_url="invalid")


def test_monitoring_config_create_rejects_invalid_scheme() -> None:
    with pytest.raises(ValidationError, match="URL must use http or https"):
        MonitoringConfigCreateDTO(health_url="ftp://service.example.com/health")


def test_monitoring_config_update_allows_none_url() -> None:
    dto = MonitoringConfigUpdateDTO()

    assert dto.health_url is None


def test_component_create_schema_accepts_valid_payload() -> None:
    dto = ComponentCreateDTO(
        product_id=10,
        name="Backend API",
        type=ComponentType.BACKEND,
        monitoring_config=MonitoringConfigCreateDTO(
            health_url="https://service.example.com/health",
            check_interval_seconds=45,
            timeout_seconds=5,
            expected_status_code=200,
            max_response_time_ms=500,
            failures_before_outage=2,
        ),
    )

    dumped = dto.model_dump(by_alias=True)

    assert dumped["productId"] == 10
    assert dumped["monitoringConfig"]["healthUrl"] == "https://service.example.com/health"
