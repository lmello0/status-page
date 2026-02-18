import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from infra.config.config import Config


def _clear_postgres_database_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_CONFIG__USER", raising=False)
    monkeypatch.delenv("DATABASE_CONFIG__PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_CONFIG__HOST", raising=False)
    monkeypatch.delenv("DATABASE_CONFIG__PORT", raising=False)
    monkeypatch.delenv("DATABASE_CONFIG__DATABASE", raising=False)


def test_database_config_sqlite_driver_ignores_postgres_fields(monkeypatch: MonkeyPatch) -> None:
    _clear_postgres_database_env(monkeypatch)
    monkeypatch.setenv("DATABASE_CONFIG__DRIVER", "sqlite")
    monkeypatch.setenv("DATABASE_CONFIG__SQLITE_PATH", "./tmp/test.sqlite3")

    config = Config(_env_file=None)

    assert config.DATABASE_CONFIG.DRIVER == "sqlite"
    assert config.DATABASE_CONFIG.SQLITE_PATH == "./tmp/test.sqlite3"
    assert config.DATABASE_CONFIG.USER is None
    assert config.DATABASE_CONFIG.PASSWORD is None
    assert config.DATABASE_CONFIG.HOST is None
    assert config.DATABASE_CONFIG.PORT is None
    assert config.DATABASE_CONFIG.DATABASE is None


def test_database_config_postgres_driver_requires_fields(monkeypatch: MonkeyPatch) -> None:
    _clear_postgres_database_env(monkeypatch)
    monkeypatch.setenv("DATABASE_CONFIG__DRIVER", "postgres")

    with pytest.raises(ValidationError, match="required when DRIVER=postgres"):
        Config(_env_file=None)
