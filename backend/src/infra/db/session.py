from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import URL, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infra.config.config import get_config
from infra.db.models import Base


@lru_cache
def get_engine() -> AsyncEngine:
    db_config = get_config().DATABASE_CONFIG

    if db_config.DRIVER == "sqlite":
        url = URL.create(
            drivername="sqlite+aiosqlite",
            database=db_config.SQLITE_PATH,
        )
        engine = create_async_engine(
            url,
            echo=db_config.ECHO,
            pool_pre_ping=True,
        )

        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    url = URL.create(
        drivername="postgresql+asyncpg",
        username=db_config.USER,
        password=db_config.PASSWORD,
        host=db_config.HOST,
        port=db_config.PORT,
        database=db_config.DATABASE,
    )

    return create_async_engine(
        url,
        echo=db_config.ECHO,
        pool_pre_ping=True,
        pool_size=db_config.POOL_SIZE,
        max_overflow=db_config.MAX_OVERFLOW,
        pool_timeout=db_config.POOL_TIMEOUT,
        pool_recycle=db_config.POOL_RECYCLE,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_engine() -> None:
    await get_engine().dispose()


async def create_database_schema() -> None:
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
