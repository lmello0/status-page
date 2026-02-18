from types import SimpleNamespace

import pytest
from fastapi import FastAPI

import infra.web.routers.stats_router as stats_router_module


class HealthyProcess:
    def memory_full_info(self) -> SimpleNamespace:
        return SimpleNamespace(rss=1024)

    def cpu_percent(self, interval: float = 0.1) -> float:
        return 12.5


class FailingProcess:
    def memory_full_info(self) -> SimpleNamespace:
        raise RuntimeError("process metrics unavailable")

    def cpu_percent(self, interval: float = 0.1) -> float:
        return 0.0


@pytest.fixture
def stats_app() -> FastAPI:
    app = FastAPI()
    app.include_router(stats_router_module.router)
    return app


@pytest.mark.asyncio
async def test_stats_health_up_response(stats_app: FastAPI, async_client_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stats_router_module, "_current_process", HealthyProcess())

    client = await async_client_factory(stats_app)
    response = await client.get("/stats/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "UP"
    assert payload["ram"] == "1.00 KB"
    assert payload["cpu_percent"] == 12.5


@pytest.mark.asyncio
async def test_stats_health_degraded_response(
    stats_app: FastAPI,
    async_client_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stats_router_module, "_current_process", FailingProcess())

    client = await async_client_factory(stats_app)
    response = await client.get("/stats/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "DEGRADED"
    assert "process metrics unavailable" in payload["error"]
