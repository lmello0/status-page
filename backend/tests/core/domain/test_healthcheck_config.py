import pytest

from core.domain.healthcheck_config import HealthcheckConfig


def test_healthcheck_config_accepts_http_and_https_urls() -> None:
    http_config = HealthcheckConfig(health_url="http://service.example.com/health")
    https_config = HealthcheckConfig(health_url="https://service.example.com/health")

    assert http_config.health_url.startswith("http://")
    assert https_config.health_url.startswith("https://")


@pytest.mark.parametrize("url", ["service.example.com", "http:/broken", "https://"])
def test_healthcheck_config_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(ValueError, match="Invalid URL"):
        HealthcheckConfig(health_url=url)


def test_healthcheck_config_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="URL must use http or https"):
        HealthcheckConfig(health_url="ftp://service.example.com/health")
