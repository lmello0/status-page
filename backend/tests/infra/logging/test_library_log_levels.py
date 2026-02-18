import logging

import pytest

from infra.logging.config import (
    OFF_LOG_LEVEL,
    _apply_library_log_levels,
    _normalize_log_level,
    configure_logging,
)


def test_normalize_log_level_supports_standard_levels_and_off() -> None:
    assert _normalize_log_level("WARNING") == logging.WARNING
    assert _normalize_log_level("off") == OFF_LOG_LEVEL
    assert _normalize_log_level(logging.ERROR) == logging.ERROR


def test_normalize_log_level_rejects_invalid_level() -> None:
    with pytest.raises(ValueError, match="Invalid log level"):
        _normalize_log_level("LOUD")


def test_apply_library_log_levels_sets_levels_and_disable_behavior() -> None:
    enabled_logger_name = "tests.logging.enabled"
    off_logger_name = "tests.logging.off"

    enabled_logger = logging.getLogger(enabled_logger_name)
    enabled_logger.disabled = True
    enabled_logger.propagate = False

    off_logger = logging.getLogger(off_logger_name)
    off_logger.addHandler(logging.StreamHandler())
    off_logger.disabled = False
    off_logger.propagate = True

    _apply_library_log_levels(
        {
            enabled_logger_name: "WARNING",
            off_logger_name: "OFF",
        }
    )

    assert enabled_logger.level == logging.WARNING
    assert enabled_logger.disabled is False
    assert enabled_logger.propagate is True

    assert off_logger.level == OFF_LOG_LEVEL
    assert off_logger.disabled is True
    assert off_logger.propagate is False
    assert off_logger.handlers == []


def test_configure_logging_applies_library_overrides_after_uvicorn_defaults() -> None:
    configure_logging(
        log_level="INFO",
        service_name="test-service",
        environment="dev",
        json_logs=False,
        library_log_levels={"uvicorn.access": "WARNING"},
    )

    uvicorn_access_logger = logging.getLogger("uvicorn.access")

    assert uvicorn_access_logger.level == logging.WARNING
    assert uvicorn_access_logger.disabled is False
    assert uvicorn_access_logger.propagate is True


def test_configure_logging_keeps_uvicorn_access_default_when_not_overridden() -> None:
    configure_logging(
        log_level="INFO",
        service_name="test-service",
        environment="dev",
        json_logs=False,
        library_log_levels={},
    )

    uvicorn_access_logger = logging.getLogger("uvicorn.access")

    assert uvicorn_access_logger.propagate is False


def test_configure_logging_fails_fast_for_invalid_library_level() -> None:
    with pytest.raises(ValueError, match="Invalid log level"):
        configure_logging(
            log_level="INFO",
            service_name="test-service",
            environment="dev",
            json_logs=False,
            library_log_levels={"httpx": "LOUD"},
        )


def test_apply_library_log_levels_rejects_blank_logger_name() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _apply_library_log_levels({" ": "INFO"})
