"""
Database session management.

Design decisions:
- Singleton engine via module-level variable (not recreated per request).
- AsyncSession + async_scoped_session for safe concurrent usage.
- Connection pool configured for production workloads.
- Sessions are always closed by the dependency injector, never leaked.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Singleton Engine ──────────────────────────────────────────────────────────
# create_async_engine is called once at module import time.
# Pool settings prevent connection exhaustion under load.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,   # validate connections before use (handles DB restarts)
    echo=settings.DEBUG,
)

# async_sessionmaker is a factory; each request creates a new AsyncSession
# from the shared connection pool.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # prevents lazy-load errors after commit
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an AsyncSession per request.
    The session is automatically closed even if the handler raises.

    Usage:
        @router.get("/")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
