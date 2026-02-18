from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from infra.utils.version import get_version


class LoggingConfig(BaseModel):
    LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    JSON_FORMAT: bool = False
    LIBRARY_LOG_LEVELS: dict[str, str | int] = Field(default_factory=dict)


class DatabaseConfig(BaseModel):
    DRIVER: Literal["postgres", "sqlite"] = "postgres"
    SQLITE_PATH: str = "./status_page.db"

    USER: str | None = None
    PASSWORD: str | None = None
    HOST: str | None = None
    PORT: int | None = None
    DATABASE: str | None = None
    ECHO: bool = False
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30
    POOL_RECYCLE: int = 1800

    @model_validator(mode="after")
    def validate_required_postgres_fields(self) -> "DatabaseConfig":
        if self.DRIVER == "sqlite":
            return self

        required_fields = {
            "USER": self.USER,
            "PASSWORD": self.PASSWORD,
            "HOST": self.HOST,
            "PORT": self.PORT,
            "DATABASE": self.DATABASE,
        }
        missing_fields = [field_name for field_name, value in required_fields.items() if value in (None, "")]

        if missing_fields:
            raise ValueError(
                f"DATABASE_CONFIG fields required when DRIVER=postgres: {', '.join(missing_fields)}"
            )

        return self


class Config(BaseSettings):
    APP_NAME: str = "py-status-page"
    VERSION: str = get_version()
    ENVIRONMENT: Literal["loc", "dev", "pre", "pro"] = "dev"
    ROOT_PATH: str = "/py-status-page"

    HOST: str = "0.0.0.0"
    PORT: int = 8080

    LOGGING_CONFIG: LoggingConfig = LoggingConfig()
    DATABASE_CONFIG: DatabaseConfig

    SYNC_INTERVAL_SECONDS: int = 60

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
