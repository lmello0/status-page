from abc import ABC, abstractmethod

from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.healthcheck_log import HealthcheckLog


class LogRepository(ABC):
    @abstractmethod
    async def add_log(self, log: HealthcheckLog) -> HealthcheckLog:
        raise NotImplementedError

    @abstractmethod
    async def get_logs(self, component_id: int, limit: int) -> list[HealthcheckLog]:
        raise NotImplementedError

    @abstractmethod
    async def get_last_n_day_summary(self, component_id: int, last_n_days: int) -> list[HealthcheckLogDaySummary]:
        raise NotImplementedError
