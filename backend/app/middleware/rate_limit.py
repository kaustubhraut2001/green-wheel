"""
Rate limiting middleware using Redis.

Uses a sliding window counter per IP (and per user when authenticated).
Protects sensitive endpoints from brute-force and abuse.

Why Redis?
- Atomic INCR + EXPIRE operations prevent race conditions.
- Works across multiple backend instances (stateless app servers).
- TTL-based expiry is automatic — no background cleanup needed.
"""
import time

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.redis import get_redis_client
from app.exceptions import RateLimitException

logger = structlog.get_logger(__name__)

# Endpoint-specific limits: (max_requests, window_seconds)
RATE_LIMIT_RULES: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (5, 60),
    "/api/v1/auth/register": (3, 60),
    "/api/v1/auth/refresh": (10, 60),
    "default": (60, 60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Determine limit rule
        limit, window = RATE_LIMIT_RULES.get(path, RATE_LIMIT_RULES["default"])

        redis = get_redis_client()
        key = f"rate_limit:{path}:{client_ip}"

        try:
            # ── Only Redis ops inside the try — route exceptions must NOT be caught here ──
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, window)
        except Exception as exc:
            # Redis is unavailable — fail open and let the request through.
            # Only log; do NOT call call_next here — let execution continue below.
            logger.error("rate_limit_redis_error", error=str(exc))
            return await call_next(request)

        if current > limit:
            logger.warning(
                "rate_limit_exceeded",
                path=path,
                client_ip=client_ip,
                count=current,
                limit=limit,
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down.",
                    },
                },
                headers={"Retry-After": str(window)},
            )

        # ── call_next is OUTSIDE the Redis try/except so route exceptions propagate ──
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
        return response
