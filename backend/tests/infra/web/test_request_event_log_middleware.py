from collections.abc import AsyncGenerator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from starlette.responses import Response

import infra.web.middleware.request_event_log_middleware as middleware_module
from infra.web.middleware.request_event_log_middleware import RequestEventLogMiddleware


class FakeRequestLogger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, event: str, **payload: Any) -> None:
        self.calls.append(("info", event, payload))

    def warning(self, event: str, **payload: Any) -> None:
        self.calls.append(("warning", event, payload))

    def error(self, event: str, **payload: Any) -> None:
        self.calls.append(("error", event, payload))

    def exception(self, event: str, **payload: Any) -> None:
        self.calls.append(("exception", event, payload))


class RaisingRequestLogger:
    def info(self, event: str, **payload: Any) -> None:
        raise RuntimeError("log emit failed")

    def warning(self, event: str, **payload: Any) -> None:
        raise RuntimeError("log emit failed")

    def error(self, event: str, **payload: Any) -> None:
        raise RuntimeError("log emit failed")

    def exception(self, event: str, **payload: Any) -> None:
        raise RuntimeError("log emit failed")


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        RequestEventLogMiddleware,
        request_id_header="x-request-id",
        excluded_path_suffixes={"/stats/health"},
    )

    @app.get("/ok")
    async def ok_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/client-error")
    async def client_error_endpoint() -> Response:
        return Response(status_code=404)

    @app.get("/server-error")
    async def server_error_endpoint() -> Response:
        return Response(status_code=503)

    @app.get("/boom")
    async def boom_endpoint() -> dict[str, str]:
        raise RuntimeError("boom")

    @app.post("/echo")
    async def echo_endpoint(payload: dict[str, Any]) -> dict[str, int]:
        return {"field_count": len(payload)}

    @app.get("/stats/health")
    async def health_endpoint() -> dict[str, str]:
        return {"status": "UP"}

    return app


@pytest.fixture
def fake_request_logger(monkeypatch: pytest.MonkeyPatch) -> FakeRequestLogger:
    fake_logger = FakeRequestLogger()
    monkeypatch.setattr(middleware_module, "request_logger", fake_logger)
    return fake_logger


@pytest.fixture
async def async_client(test_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_success_request_emits_single_summary_log_with_milestones(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.get(
        "/ok?foo=1&foo=2&bar=3",
        headers={"x-request-id": "req-success-1", "user-agent": "pytest-agent"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-success-1"

    assert len(fake_request_logger.calls) == 1
    level, event, payload = fake_request_logger.calls[0]

    assert level == "info"
    assert event == "http_request_summary"
    assert payload["request_id"] == "req-success-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/ok"
    assert payload["route_path"] == "/ok"
    assert payload["route_name"] == "ok_endpoint"
    assert payload["status_code"] == 200
    assert payload["outcome"] == "success"
    assert payload["client_ip"] is not None
    assert payload["user_agent"] == "pytest-agent"
    assert payload["error"] is None

    request_metadata = payload["request_metadata"]
    assert request_metadata["query_keys"] == ["bar", "foo"]
    assert request_metadata["content_type"] is None
    assert request_metadata["content_length"] is None

    history_events = [event_data["event"] for event_data in payload["history"]]
    assert history_events == [
        "request_received",
        "route_resolved",
        "response_started",
        "request_completed",
    ]


@pytest.mark.asyncio
async def test_client_error_response_logs_single_warning_entry(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.get("/client-error", headers={"x-request-id": "req-client-error"})

    assert response.status_code == 404
    assert response.headers["x-request-id"] == "req-client-error"

    assert len(fake_request_logger.calls) == 1
    level, event, payload = fake_request_logger.calls[0]

    assert level == "warning"
    assert event == "http_request_summary"
    assert payload["status_code"] == 404
    assert payload["outcome"] == "client_error"
    assert payload["error"] is None


@pytest.mark.asyncio
async def test_server_error_response_logs_error_with_server_outcome(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.get("/server-error")

    assert response.status_code == 503
    assert len(fake_request_logger.calls) == 1

    level, _, payload = fake_request_logger.calls[0]

    assert level == "error"
    assert payload["outcome"] == "server_error"
    assert payload["error"]["error_message"] == "Server error response with status 503"


@pytest.mark.asyncio
async def test_unhandled_exception_logs_single_exception_entry(
    test_app: FastAPI,
    fake_request_logger: FakeRequestLogger,
) -> None:
    transport = httpx.ASGITransport(app=test_app, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        response = await test_client.get("/boom", headers={"x-request-id": "req-boom"})

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-boom"
    assert len(fake_request_logger.calls) == 1

    level, event, payload = fake_request_logger.calls[0]
    assert level == "exception"
    assert event == "http_request_summary"
    assert payload["request_id"] == "req-boom"
    assert payload["status_code"] == 500
    assert payload["outcome"] == "unhandled_exception"
    assert payload["error"]["error_class"] == "RuntimeError"
    assert payload["error"]["error_message"] == "boom"

    history_events = [event_data["event"] for event_data in payload["history"]]
    assert "response_started" in history_events
    assert "exception_raised" in history_events
    assert history_events[-1] == "request_completed"


@pytest.mark.asyncio
async def test_generated_request_id_is_returned_and_logged(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.get("/ok")

    assert response.status_code == 200
    generated_request_id = response.headers.get("x-request-id")
    assert generated_request_id is not None
    assert generated_request_id != ""

    assert len(fake_request_logger.calls) == 1
    _, _, payload = fake_request_logger.calls[0]
    assert payload["request_id"] == generated_request_id


@pytest.mark.asyncio
async def test_metadata_only_logging_avoids_request_body_content(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.post("/echo?token=abc", json={"secret": "value", "apiKey": "123"})

    assert response.status_code == 200
    assert len(fake_request_logger.calls) == 1

    _, _, payload = fake_request_logger.calls[0]
    request_metadata = payload["request_metadata"]

    assert request_metadata["query_keys"] == ["token"]
    assert request_metadata["content_type"] is not None
    assert request_metadata["content_length"] is not None

    serialized_payload = str(payload)
    assert "secret" not in serialized_payload
    assert "value" not in serialized_payload
    assert "apiKey" not in serialized_payload
    assert "123" not in serialized_payload


@pytest.mark.asyncio
async def test_excluded_health_path_does_not_emit_summary_log(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response = await async_client.get("/stats/health")

    assert response.status_code == 200
    assert "x-request-id" not in response.headers
    assert fake_request_logger.calls == []


@pytest.mark.asyncio
async def test_request_context_isolated_between_requests(
    async_client: httpx.AsyncClient,
    fake_request_logger: FakeRequestLogger,
) -> None:
    response_one = await async_client.get("/ok", headers={"x-request-id": "req-one"})
    response_two = await async_client.get("/ok", headers={"x-request-id": "req-two"})

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    assert len(fake_request_logger.calls) == 2

    first_payload = fake_request_logger.calls[0][2]
    second_payload = fake_request_logger.calls[1][2]

    assert first_payload["request_id"] == "req-one"
    assert second_payload["request_id"] == "req-two"
    assert first_payload["request_id"] != second_payload["request_id"]


@pytest.mark.asyncio
async def test_logging_failure_does_not_break_request_flow(
    test_app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(middleware_module, "request_logger", RaisingRequestLogger())
    transport = httpx.ASGITransport(app=test_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        response = await test_client.get("/ok")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_non_http_scope_is_forwarded_without_logging(fake_request_logger: FakeRequestLogger) -> None:
    called = {"count": 0}

    async def app(scope, receive, send):
        called["count"] += 1

    middleware = RequestEventLogMiddleware(app)

    async def receive():
        return {"type": "websocket.receive"}

    async def send(_):
        return None

    await middleware({"type": "websocket"}, receive, send)

    assert called["count"] == 1
    assert fake_request_logger.calls == []
