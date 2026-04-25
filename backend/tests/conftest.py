from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.logging import configure_logging
from app.db.base import Base
from app.main import app
from app.core.deps import get_db

configure_logging("testing")

# asyncpg requires SelectorEventLoop on Windows (ProactorEventLoop not supported)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())



@pytest.fixture(scope="session")
def postgres_url() -> Generator[str, None, None]:
    try:
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer("pgvector/pgvector:pg15") as container:
            raw_url = container.get_connection_url()
            # testcontainers returns psycopg2 URL; we need asyncpg
            url = raw_url.replace("psycopg2", "asyncpg").replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            if "postgresql+asyncpg+asyncpg" in url:
                url = url.replace("postgresql+asyncpg+asyncpg", "postgresql+asyncpg")
            yield url
    except Exception:
        # Fallback to local dev DB when Docker is unavailable
        yield "postgresql+asyncpg://noc:noc_dev_password@localhost:5432/noc_db"


@pytest_asyncio.fixture(scope="session")
async def db_engine(postgres_url: str) -> AsyncGenerator[Any, None]:
    test_engine = create_async_engine(postgres_url, echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    TestSession = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine: Any) -> AsyncGenerator[AsyncClient, None]:
    TestSession = async_sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
