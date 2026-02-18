from core.domain.status_type import StatusType


def test_status_type_severity_ordering() -> None:
    assert StatusType.OPERATIONAL.severity < StatusType.DEGRADED.severity < StatusType.OUTAGE.severity
