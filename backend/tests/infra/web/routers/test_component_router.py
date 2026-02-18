from datetime import datetime, timezone

import pytest
from fastapi import FastAPI

import infra.web.routers.component_router as component_router_module
from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.status_type import StatusType
from tests.support.fakes import FakeComponentRepository, FakeLogRepository


@pytest.fixture
def component_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    component_repo = FakeComponentRepository(
        initial_components=[
            Component(
                id=1,
                product_id=50,
                name="payments-api",
                type=ComponentType.BACKEND,
                monitoring_config=HealthcheckConfig(health_url="https://payments.example.com/health"),
                current_status=StatusType.OPERATIONAL,
            ),
            Component(
                id=2,
                product_id=50,
                name="payments-web",
                type=ComponentType.FRONTEND,
                monitoring_config=HealthcheckConfig(health_url="https://frontend.example.com/health"),
                current_status=StatusType.OPERATIONAL,
            ),
        ]
    )

    log_repo = FakeLogRepository(
        precomputed_summary={
            1: [
                HealthcheckLogDaySummary(
                    component_id=1,
                    date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    total_checks=3,
                    successful_checks=3,
                    uptime=100.0,
                    avg_response_time=12,
                    max_response_time=20,
                    overall_status=StatusType.OPERATIONAL,
                )
            ]
        }
    )

    monkeypatch.setattr(component_router_module, "get_component_repository", lambda: component_repo)
    monkeypatch.setattr(component_router_module, "get_log_repository", lambda: log_repo)

    app = FastAPI()
    app.include_router(component_router_module.router)
    return app


@pytest.mark.asyncio
async def test_create_component(component_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(component_app)

    response = await client.post(
        "/component",
        json={
            "productId": 50,
            "name": "new-service",
            "type": "BACKEND",
            "monitoringConfig": {
                "healthUrl": "https://new-service.example.com/health",
                "checkIntervalSeconds": 30,
                "timeoutSeconds": 3,
                "expectedStatusCode": 200,
                "maxResponseTimeMs": 400,
                "failuresBeforeOutage": 2,
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "new-service"


@pytest.mark.asyncio
async def test_create_component_returns_conflict_on_duplicate_name(
    component_app: FastAPI,
    async_client_factory,
) -> None:
    client = await async_client_factory(component_app)

    response = await client.post(
        "/component",
        json={
            "productId": 50,
            "name": "payments-api",
            "type": "BACKEND",
            "monitoringConfig": {
                "healthUrl": "https://another.example.com/health",
                "checkIntervalSeconds": 30,
                "timeoutSeconds": 3,
                "expectedStatusCode": 200,
                "maxResponseTimeMs": 400,
                "failuresBeforeOutage": 2,
            },
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_all_components(component_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(component_app)

    response = await client.get("/component", params={"product_id": 50})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pageCount"] == 2
    first_summary = payload["content"][0]["healthcheckDayLogs"][0]
    assert first_summary["uptime"] == 100.0
    assert first_summary["overallStatus"] == "OPERATIONAL"


@pytest.mark.asyncio
async def test_update_component_returns_404_when_missing(component_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(component_app)

    response = await client.patch("/component/999", json={"name": "missing"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_component_returns_conflict_for_duplicate_name(
    component_app: FastAPI,
    async_client_factory,
) -> None:
    client = await async_client_factory(component_app)

    response = await client.patch("/component/2", json={"name": "payments-api"})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_component_returns_204(component_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(component_app)

    response = await client.delete("/component/1")

    assert response.status_code == 204
