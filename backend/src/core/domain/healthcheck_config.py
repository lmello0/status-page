from dataclasses import dataclass


@dataclass
class HealthcheckConfig:
    health_url: str
    check_interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_code: int = 200
    max_response_time_ms: int = 5000
    failures_before_outage: int = 3