"""
Redis client singleton.

Why singleton?
- Redis connection pools are expensive to create.
- A single pool shared across the application avoids reconnection overhead.
- Redis is used for two distinct purposes here:
    1. Cache (DB 0) — exchange rates, user profiles
    2. Celery broker (DB 1) — task queuing (configured in celery_app.py)
"""
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """
    Return the singleton Redis client.
    Initialised once on first call; subsequent calls return the cached instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis client initialised", url=settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Called on application shutdown to cleanly drain the connection pool."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")
