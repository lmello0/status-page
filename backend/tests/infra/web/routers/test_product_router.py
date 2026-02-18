from datetime import datetime, timezone

import pytest
from fastapi import FastAPI

import infra.web.routers.product_router as product_router_module
from core.domain.component import Component
from core.domain.component_type import ComponentType
from core.domain.healthcheck_config import HealthcheckConfig
from core.domain.healthcheck_day_summary import HealthcheckLogDaySummary
from core.domain.product import Product
from core.domain.status_type import StatusType
from tests.support.fakes import FakeLogRepository, FakeProductRepository


@pytest.fixture
def product_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    product_repo = FakeProductRepository(
        initial_products=[
            Product(
                id=1,
                name="Payments",
                description="Payments API",
                is_visible=True,
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                components=[
                    Component(
                        id=10,
                        product_id=1,
                        name="payments-api",
                        type=ComponentType.BACKEND,
                        monitoring_config=HealthcheckConfig(
                            health_url="https://payments.example.com/health"
                        ),
                        current_status=StatusType.OPERATIONAL,
                    )
                ],
            )
        ]
    )
    log_repo = FakeLogRepository(
        precomputed_summary={
            10: [
                HealthcheckLogDaySummary(
                    component_id=10,
                    date=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    total_checks=5,
                    successful_checks=5,
                    uptime=100.0,
                    avg_response_time=20,
                    max_response_time=30,
                    overall_status=StatusType.OPERATIONAL,
                )
            ]
        }
    )

    monkeypatch.setattr(product_router_module, "get_product_repository", lambda: product_repo)
    monkeypatch.setattr(product_router_module, "get_log_repository", lambda: log_repo)

    app = FastAPI()
    app.include_router(product_router_module.router)
    return app


@pytest.mark.asyncio
async def test_create_product(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.post("/product", json={"name": "New Product", "description": "desc"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "New Product"
    assert payload["description"] == "desc"
    assert payload["isVisible"] is True


@pytest.mark.asyncio
async def test_get_all_products_returns_page_with_component_summaries(
    product_app: FastAPI,
    async_client_factory,
) -> None:
    client = await async_client_factory(product_app)

    response = await client.get("/product", params={"summary_days": 30})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pageCount"] == 1
    assert payload["content"][0]["name"] == "Payments"
    first_summary = payload["content"][0]["components"][0]["healthcheckDayLogs"][0]
    assert first_summary["uptime"] == 100.0
    assert first_summary["overallStatus"] == "OPERATIONAL"


@pytest.mark.asyncio
async def test_get_product_by_id_returns_404_when_missing(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.get("/product/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


@pytest.mark.asyncio
async def test_get_product_by_name(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.get("/product/name/Payments")

    assert response.status_code == 200
    assert response.json()["name"] == "Payments"


@pytest.mark.asyncio
async def test_update_product_validation_error_on_empty_payload(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.patch("/product/1", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_product_returns_404_for_missing_product(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.patch("/product/999", json={"description": "x"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_returns_204(product_app: FastAPI, async_client_factory) -> None:
    client = await async_client_factory(product_app)

    response = await client.delete("/product/1")

    assert response.status_code == 204
