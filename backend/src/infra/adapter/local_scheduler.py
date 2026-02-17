from functools import lru_cache
from typing import Any, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler, BaseScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.port.scheduler import Scheduler


class LocalScheduler(Scheduler):
    def __init__(self, scheduler: BaseScheduler) -> None:
        self.scheduler = scheduler
        self._jobs: dict[str, str] = {}

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown(wait=True)

    def add_job(
        self,
        job_key: str,
        func: Callable[..., Any],
        interval_seconds: int,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        job_name: Optional[str] = None,
    ) -> None:
        if job_key in self._jobs:
            self.remove_job(job_key)

        kwargs = kwargs or {}
        job_name = job_name or job_key

        job = self.scheduler.add_job(
            func=func,
            trigger=IntervalTrigger(seconds=interval_seconds),
            args=args,
            kwags=kwargs,
            id=job_key,
            name=job_name,
            replace_existing=True,
            max_instances=1,
        )

        self._jobs[job_key] = job.id

        return job.id

    def remove_job(self, job_key: str) -> bool:
        if job_key in self._jobs:
            job_id = self._jobs.pop(job_key)

            try:
                self.scheduler.remove_job(job_id)
                return True
            except Exception:
                return False

        return False

    def has_job(self, job_key: str) -> bool:
        return job_key in self._jobs

    def get_all_jobs(self) -> list[str]:
        return list(self._jobs.keys())


@lru_cache
def get_local_scheduler() -> Scheduler:
    scheduler = AsyncIOScheduler()

    return LocalScheduler(scheduler)
