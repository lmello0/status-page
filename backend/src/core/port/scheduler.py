from abc import ABC, abstractmethod
from typing import Callable, Optional


class Scheduler(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_job(
        self,
        job_key: str,
        func: Callable,
        interval_seconds: int,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        job_name: Optional[str] = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_job(self, job_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def has_job(self, job_key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_all_jobs(self) -> list[str]:
        raise NotImplementedError
