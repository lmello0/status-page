from types import SimpleNamespace

import pytest

import infra.web.app as app_module
from infra.adapter.dict_component_cache import DictComponentCache
from infra.web.middleware.request_event_log_middleware import RequestEventLogMiddleware
from tests.support.fakes import FakeComponentRepository, FakeLogRepository, FakeScheduler


class FakeHttpClient:
    instances: list["FakeHttpClient"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.closed = False
        FakeHttpClient.instances.append(self)

    async def aclose(self) -> None:
        self.closed = True


class FakeHealthcheckService:
    instances: list["FakeHealthcheckService"] = []

    def __init__(
        self,
        sync_interval_seconds,
        scheduler,
        cache,
        http_client,
        get_components_use_case,
        update_component_use_case,
    ) -> None:
        self.sync_interval_seconds = sync_interval_seconds
        self.scheduler = scheduler
        self.cache = cache
        self.http_client = http_client
        self.get_components_use_case = get_components_use_case
        self.update_component_use_case = update_component_use_case
        self.started = False
        FakeHealthcheckService.instances.append(self)

    async def start(self) -> None:
        self.started = True


@pytest.mark.asyncio
async def test_create_app_wires_routers_middleware_and_lifespan(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeHttpClient.instances.clear()
    FakeHealthcheckService.instances.clear()

    scheduler = FakeScheduler()
    close_engine_calls = {"count": 0}
    create_database_schema_calls = {"count": 0}
    configure_calls: list[dict] = []

    async def fake_close_engine() -> None:
        close_engine_calls["count"] += 1

    async def fake_create_database_schema() -> None:
        create_database_schema_calls["count"] += 1

    def fake_configure_logging(**kwargs) -> None:
        configure_calls.append(kwargs)

    config = SimpleNamespace(
        APP_NAME="status-page",
        VERSION="9.9.9",
        ENVIRONMENT="dev",
        ROOT_PATH="/status",
        HOST="127.0.0.1",
        PORT=9999,
        SYNC_INTERVAL_SECONDS=15,
        LOGGING_CONFIG=SimpleNamespace(
            LEVEL="INFO",
            JSON_FORMAT=False,
            LIBRARY_LOG_LEVELS={"httpx": "WARNING"},
        ),
    )

    monkeypatch.setattr(app_module, "get_config", lambda: config)
    monkeypatch.setattr(app_module, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(app_module, "get_local_scheduler", lambda: scheduler)
    monkeypatch.setattr(app_module, "get_dict_component_cache", lambda: DictComponentCache())
    monkeypatch.setattr(app_module, "get_component_repository", lambda: FakeComponentRepository())
    monkeypatch.setattr(app_module, "get_log_repository", lambda: FakeLogRepository())
    monkeypatch.setattr(app_module, "HealthcheckService", FakeHealthcheckService)
    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(app_module, "close_engine", fake_close_engine)
    monkeypatch.setattr(app_module, "create_database_schema", fake_create_database_schema)

    app = app_module.create_app()

    assert app.title == "status-page"
    assert app.version == "9.9.9"
    assert app.root_path == "/status"
    assert app.state.host == "127.0.0.1"
    assert app.state.port == 9999

    route_paths = {route.path for route in app.routes}
    assert "/stats/health" in route_paths
    assert "/product" in route_paths
    assert "/component" in route_paths

    assert any(m.cls is RequestEventLogMiddleware for m in app.user_middleware)

    assert configure_calls == [
        {
            "log_level": "INFO",
            "json_logs": False,
            "service_name": "status-page",
            "environment": "dev",
            "library_log_levels": {"httpx": "WARNING"},
        }
    ]

    async with app.router.lifespan_context(app):
        assert scheduler.started is True
        assert len(FakeHealthcheckService.instances) == 1
        assert FakeHealthcheckService.instances[0].started is True

    assert create_database_schema_calls["count"] == 1
    assert scheduler.stopped is True
    assert close_engine_calls["count"] == 1
    assert len(FakeHttpClient.instances) == 1
    assert FakeHttpClient.instances[0].closed is True


@pytest.mark.asyncio
@pytest.mark.parametrize("environment", ["pre", "pro"])
async def test_create_app_does_not_create_schema_outside_dev_or_loc(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    FakeHttpClient.instances.clear()
    FakeHealthcheckService.instances.clear()

    scheduler = FakeScheduler()
    create_database_schema_calls = {"count": 0}

    async def fake_create_database_schema() -> None:
        create_database_schema_calls["count"] += 1

    async def fake_close_engine() -> None:
        return None

    config = SimpleNamespace(
        APP_NAME="status-page",
        VERSION="9.9.9",
        ENVIRONMENT=environment,
        ROOT_PATH="/status",
        HOST="127.0.0.1",
        PORT=9999,
        SYNC_INTERVAL_SECONDS=15,
        LOGGING_CONFIG=SimpleNamespace(
            LEVEL="INFO",
            JSON_FORMAT=False,
            LIBRARY_LOG_LEVELS={"httpx": "WARNING"},
        ),
    )

    monkeypatch.setattr(app_module, "get_config", lambda: config)
    monkeypatch.setattr(app_module, "configure_logging", lambda **kwargs: None)
    monkeypatch.setattr(app_module, "get_local_scheduler", lambda: scheduler)
    monkeypatch.setattr(app_module, "get_dict_component_cache", lambda: DictComponentCache())
    monkeypatch.setattr(app_module, "get_component_repository", lambda: FakeComponentRepository())
    monkeypatch.setattr(app_module, "get_log_repository", lambda: FakeLogRepository())
    monkeypatch.setattr(app_module, "HealthcheckService", FakeHealthcheckService)
    monkeypatch.setattr(app_module.httpx, "AsyncClient", FakeHttpClient)
    monkeypatch.setattr(app_module, "create_database_schema", fake_create_database_schema)
    monkeypatch.setattr(app_module, "close_engine", fake_close_engine)

    app = app_module.create_app()

    async with app.router.lifespan_context(app):
        pass

    assert create_database_schema_calls["count"] == 0
