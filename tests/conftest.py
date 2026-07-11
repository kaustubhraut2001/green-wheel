"""
Shared test fixtures.

Design decisions:
- Use a separate test database (in-memory SQLite for unit tests, PostgreSQL for integration).
- Override FastAPI dependencies so tests never hit real DB/Redis/external APIs.
- Fixtures are scoped appropriately:
    - "session" scope for engine (created once per test session)
    - "function" scope for DB transactions (rolled back after each test)
"""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import create_application
from app.models import User
from app.core.security import create_access_token, hash_password

# ── Test DB (SQLite in-memory for speed) ─────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Each test gets its own session with automatic rollback.
    This means tests are isolated without needing to clean up data manually.
    """
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def mock_redis():
    """Mock Redis client — prevents tests from needing a real Redis instance."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest_asyncio.fixture
async def app(db_session, mock_redis):
    """FastAPI app with overridden dependencies."""
    from app.db.redis import get_redis_client

    application = create_application()

    # Override DB dependency
    async def override_get_db():
        yield db_session

    # Override Redis
    def override_redis():
        return mock_redis

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_redis_client] = override_redis

    return application


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the DB."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("Test@1234"),
        first_name="Test",
        last_name="User",
        default_currency="USD",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Return Authorization headers for the test user."""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
