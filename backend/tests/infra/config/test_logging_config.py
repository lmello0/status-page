from pytest import MonkeyPatch

from infra.config.config import Config


def _set_required_database_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_CONFIG__USER", "status_page_user")
    monkeypatch.setenv("DATABASE_CONFIG__PASSWORD", "1234")
    monkeypatch.setenv("DATABASE_CONFIG__HOST", "localhost")
    monkeypatch.setenv("DATABASE_CONFIG__PORT", "5432")
    monkeypatch.setenv("DATABASE_CONFIG__DATABASE", "status_page")


def test_logging_config_parses_library_log_levels_from_env(monkeypatch: MonkeyPatch) -> None:
    _set_required_database_env(monkeypatch)
    monkeypatch.setenv(
        "LOGGING_CONFIG__LIBRARY_LOG_LEVELS",
        '{"httpx":"WARNING","sqlalchemy.engine":"ERROR","custom.logger":25}',
    )

    config = Config(_env_file=None)

    assert config.LOGGING_CONFIG.LIBRARY_LOG_LEVELS == {
        "httpx": "WARNING",
        "sqlalchemy.engine": "ERROR",
        "custom.logger": 25,
    }


def test_logging_config_library_log_levels_default_to_empty_dict(monkeypatch: MonkeyPatch) -> None:
    _set_required_database_env(monkeypatch)
    monkeypatch.delenv("LOGGING_CONFIG__LIBRARY_LOG_LEVELS", raising=False)

    config = Config(_env_file=None)

    assert config.LOGGING_CONFIG.LIBRARY_LOG_LEVELS == {}
