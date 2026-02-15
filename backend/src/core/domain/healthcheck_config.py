from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class HealthcheckConfig:
    health_url: str
    check_interval_seconds: int = 60
    timeout_seconds: int = 30
    expected_status_code: int = 200
    max_response_time_ms: int = 5000
    failures_before_outage: int = 3

    def __post_init__(self):
        parsed = urlparse(self.health_url)
        if not all([parsed.scheme, parsed.netloc]):
            raise ValueError(f"Invalid URL: {self.health_url}")

        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL must use http or https scheme: {self.health_url}")
