from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

import infra.db.session as session_module


class FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


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
