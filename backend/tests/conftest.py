from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import infra.db.session as db_session
from infra.adapter.dict_component_cache import get_dict_component_cache
from infra.adapter.local_scheduler import get_local_scheduler
from infra.adapter.postgres_component_repository import get_component_repository
from infra.adapter.postgres_log_repository import get_log_repository
from infra.adapter.postgres_product_repository import get_product_repository
from infra.config.config import get_config
from infra.db.models import Base


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_CONFIG__DRIVER", "postgres")
    monkeypatch.setenv("DATABASE_CONFIG__SQLITE_PATH", "./status_page.db")
    monkeypatch.setenv("DATABASE_CONFIG__USER", "status_page_user")
    monkeypatch.setenv("DATABASE_CONFIG__PASSWORD", "1234")
    monkeypatch.setenv("DATABASE_CONFIG__HOST", "localhost")
    monkeypatch.setenv("DATABASE_CONFIG__PORT", "5432")
    monkeypatch.setenv("DATABASE_CONFIG__DATABASE", "status_page")


@pytest.fixture(autouse=True)
def _reset_cached_singletons() -> AsyncGenerator[None, None]:
    cacheables = [
        get_config,
        db_session.get_engine,
        db_session.get_session_factory,
        get_product_repository,
        get_component_repository,
        get_log_repository,
        get_dict_component_cache,
        get_local_scheduler,
    ]

    for cacheable in cacheables:
        cacheable.cache_clear()

    yield

    for cacheable in cacheables:
        cacheable.cache_clear()


@pytest.fixture(autouse=True)
def _block_postgres_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    original_create_async_engine = db_session.create_async_engine

    def guarded_create_async_engine(url, *args, **kwargs):
        if "postgresql+asyncpg" in str(url):
            raise RuntimeError("Tests must not create PostgreSQL engines")

        return original_create_async_engine(url, *args, **kwargs)

    monkeypatch.setattr(db_session, "create_async_engine", guarded_create_async_engine)


@pytest.fixture
async def sqlite_engine() -> AsyncGenerator[AsyncEngine, None]:
    pytest.importorskip("aiosqlite")

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def sqlite_session_factory(sqlite_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=sqlite_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def async_client_factory() -> AsyncGenerator:
    clients: list[httpx.AsyncClient] = []

    async def _factory(app, *, raise_app_exceptions: bool = True) -> httpx.AsyncClient:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        clients.append(client)
        return client

    try:
        yield _factory
    finally:
        for client in clients:
            await client.aclose()
