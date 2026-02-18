from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

import infra.db.session as session_module


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False
        self.sync_engine = object()

    async def dispose(self) -> None:
        self.disposed = True


class FakeConnection:
    def __init__(self) -> None:
        self.run_sync_calls: list[object] = []

    async def run_sync(self, fn) -> None:
        self.run_sync_calls.append(fn)


class FakeBeginContext:
    def __init__(self, connection: FakeConnection) -> None:
        self._connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self._connection

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeEngineWithBegin(FakeEngine):
    def __init__(self, connection: FakeConnection) -> None:
        super().__init__()
        self._connection = connection

    def begin(self) -> FakeBeginContext:
        return FakeBeginContext(self._connection)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeSessionFactory:
    def __init__(self, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSession:
        return self._session


@pytest.mark.asyncio
async def test_get_engine_uses_configured_connection_values(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_engine = FakeEngine()

    config = SimpleNamespace(
        DATABASE_CONFIG=SimpleNamespace(
            DRIVER="postgres",
            SQLITE_PATH="./status_page.db",
            USER="db_user",
            PASSWORD="db_password",
            HOST="localhost",
            PORT=5432,
            DATABASE="status",
            ECHO=True,
            POOL_SIZE=5,
            MAX_OVERFLOW=10,
            POOL_TIMEOUT=12,
            POOL_RECYCLE=120,
        )
    )

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = str(url)
        captured["kwargs"] = kwargs
        return fake_engine

    monkeypatch.setattr(session_module, "get_config", lambda: config)
    monkeypatch.setattr(session_module, "create_async_engine", fake_create_async_engine)

    engine = session_module.get_engine()

    assert engine is fake_engine
    assert "postgresql+asyncpg://db_user" in str(captured["url"])
    assert captured["kwargs"] == {
        "echo": True,
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 12,
        "pool_recycle": 120,
    }


@pytest.mark.asyncio
async def test_get_engine_uses_sqlite_driver_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    listeners: list[tuple[object, str, object]] = []
    fake_engine = FakeEngine()

    config = SimpleNamespace(
        DATABASE_CONFIG=SimpleNamespace(
            DRIVER="sqlite",
            SQLITE_PATH="./tmp/status_page.db",
            USER=None,
            PASSWORD=None,
            HOST=None,
            PORT=None,
            DATABASE=None,
            ECHO=False,
            POOL_SIZE=5,
            MAX_OVERFLOW=10,
            POOL_TIMEOUT=12,
            POOL_RECYCLE=120,
        )
    )

    def fake_create_async_engine(url, **kwargs):
        captured["url"] = str(url)
        captured["kwargs"] = kwargs
        return fake_engine

    def fake_listens_for(target, identifier):
        def _decorator(fn):
            listeners.append((target, identifier, fn))
            return fn

        return _decorator

    monkeypatch.setattr(session_module, "get_config", lambda: config)
    monkeypatch.setattr(session_module, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(session_module.event, "listens_for", fake_listens_for)

    engine = session_module.get_engine()

    assert engine is fake_engine
    assert str(captured["url"]) == "sqlite+aiosqlite:///./tmp/status_page.db"
    assert captured["kwargs"] == {
        "echo": False,
        "pool_pre_ping": True,
    }
    assert len(listeners) == 1
    assert listeners[0][0] is fake_engine.sync_engine
    assert listeners[0][1] == "connect"


@pytest.mark.asyncio
async def test_session_scope_commits_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(session_module, "get_session_factory", lambda: FakeSessionFactory(fake_session))

    async with session_module.session_scope() as session:
        assert session is fake_session

    assert fake_session.committed is True
    assert fake_session.rolled_back is False


@pytest.mark.asyncio
async def test_session_scope_rolls_back_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(session_module, "get_session_factory", lambda: FakeSessionFactory(fake_session))

    with pytest.raises(RuntimeError, match="boom"):
        async with session_module.session_scope():
            raise RuntimeError("boom")

    assert fake_session.committed is False
    assert fake_session.rolled_back is True


@pytest.mark.asyncio
async def test_get_session_yields_session_from_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = FakeSession()
    monkeypatch.setattr(session_module, "get_session_factory", lambda: FakeSessionFactory(fake_session))

    iterator: AsyncIterator[FakeSession] = session_module.get_session()
    yielded = await anext(iterator)

    assert yielded is fake_session

    with pytest.raises(StopAsyncIteration):
        await anext(iterator)


@pytest.mark.asyncio
async def test_close_engine_disposes_cached_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_engine = FakeEngine()
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)

    await session_module.close_engine()

    assert fake_engine.disposed is True


@pytest.mark.asyncio
async def test_create_database_schema_runs_create_all(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_connection = FakeConnection()
    fake_engine = FakeEngineWithBegin(fake_connection)
    monkeypatch.setattr(session_module, "get_engine", lambda: fake_engine)

    await session_module.create_database_schema()

    assert len(fake_connection.run_sync_calls) == 1
    run_sync_argument = fake_connection.run_sync_calls[0]
    assert getattr(run_sync_argument, "__name__", "") == "create_all"
    assert getattr(run_sync_argument, "__self__", None) is session_module.Base.metadata
