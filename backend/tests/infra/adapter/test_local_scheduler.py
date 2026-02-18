from dataclasses import dataclass

from infra.adapter.local_scheduler import LocalScheduler


@dataclass
class FakeJob:
    id: str


class FakeBaseScheduler:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.add_calls: list[dict] = []
        self.removed_ids: list[str] = []
        self.raise_on_remove = False

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = True) -> None:
        self.stopped = wait

    def add_job(self, **kwargs):
        self.add_calls.append(kwargs)
        return FakeJob(id=kwargs["id"])

    def remove_job(self, job_id: str) -> None:
        if self.raise_on_remove:
            raise RuntimeError("remove failed")

        self.removed_ids.append(job_id)


def test_local_scheduler_start_stop_and_add_job_with_kwargs() -> None:
    backend = FakeBaseScheduler()
    scheduler = LocalScheduler(backend)

    scheduler.start()
    scheduler.add_job(
        job_key="job-1",
        func=lambda: None,
        interval_seconds=30,
        args=(1,),
        kwargs={"x": 1},
        job_name="Job One",
    )
    scheduler.stop()

    assert backend.started is True
    assert backend.stopped is True
    assert backend.add_calls[0]["kwargs"] == {"x": 1}
    assert scheduler.has_job("job-1") is True


def test_local_scheduler_replaces_existing_job_before_add() -> None:
    backend = FakeBaseScheduler()
    scheduler = LocalScheduler(backend)

    scheduler.add_job("job-1", lambda: None, 10)
    scheduler.add_job("job-1", lambda: None, 20)

    assert backend.removed_ids == ["job-1"]
    assert len(backend.add_calls) == 2
    assert scheduler.get_all_jobs() == ["job-1"]


def test_local_scheduler_remove_job_handles_errors() -> None:
    backend = FakeBaseScheduler()
    scheduler = LocalScheduler(backend)

    scheduler.add_job("job-1", lambda: None, 10)
    backend.raise_on_remove = True

    assert scheduler.remove_job("job-1") is False
    assert scheduler.has_job("job-1") is False


def test_local_scheduler_remove_nonexistent_job_returns_false() -> None:
    scheduler = LocalScheduler(FakeBaseScheduler())

    assert scheduler.remove_job("missing") is False
