from functools import lru_cache
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from infra.utils.version import get_version


class LoggingConfig(BaseModel):
    LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    JSON_FORMAT: bool = False


class DatabaseConfig(BaseModel):
    USER: str
    PASSWORD: str
    HOST: str
    PORT: int
    DATABASE: str
    ECHO: bool = False
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800


class Config(BaseSettings):
    APP_NAME: str = "py-status-page"
    VERSION: str = get_version()
    ENVIRONMENT: Literal["loc", "dev", "pre", "pro"] = "dev"
    ROOT_PATH: str = "/py-status-page"

    HOST: str = "0.0.0.0"
    PORT: int = 8080

    LOGGING_CONFIG: LoggingConfig = LoggingConfig()
    DATABASE_CONFIG: DatabaseConfig

    model_config = SettingsConfigDict(
        frozen=True,
        extra="ignore",
        case_sensitive=False,
        env_file=".env",
        env_nested_delimiter="__",
    )


@lru_cache
def get_config() -> Config:
    return Config()  # type: ignore
