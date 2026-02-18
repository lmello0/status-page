from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.product import Product
from core.domain.status_type import StatusType


def _component(component_id: int, status: StatusType | None) -> Component:
    return Component(
        id=component_id,
        product_id=1,
        name=f"component-{component_id}",
        type=ComponentType.BACKEND,
        monitoring_config=HealthcheckConfig(health_url=f"https://service-{component_id}.example.com/health"),
        current_status=status,
    )


def test_get_overall_status_returns_operational_when_no_components() -> None:
    product = Product(id=1, name="api", components=[])

    assert product.get_overall_status() is StatusType.OPERATIONAL


def test_get_overall_status_returns_highest_severity_component_status() -> None:
    product = Product(
        id=1,
        name="api",
        components=[
            _component(1, StatusType.OPERATIONAL),
            _component(2, StatusType.DEGRADED),
            _component(3, StatusType.OUTAGE),
        ],
    )

    assert product.get_overall_status() is StatusType.OUTAGE
