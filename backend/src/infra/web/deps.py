from functools import lru_cache

from infra.config.config import Config


@lru_cache
def get_config() -> Config:
    return Config()
