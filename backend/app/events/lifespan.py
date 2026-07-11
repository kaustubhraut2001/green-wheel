"""
Application startup and shutdown events.
Registered with FastAPI lifespan for clean resource management.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.logging import configure_logging
from app.db.redis import close_redis, get_redis_client

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Code before yield runs on startup, code after yield runs on shutdown.
    """
    # ── Startup ───────────────────────────────────────────────
    configure_logging()
    logger.info("application_starting")

    # Warm up Redis connection
    redis = get_redis_client()
    await redis.ping()
    logger.info("redis_connected")

    logger.info("application_ready")
    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("application_shutting_down")
    await close_redis()
    logger.info("application_stopped")
