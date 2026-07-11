"""
Health check endpoints.

/health  — basic liveness (is the process running?)
/ready   — readiness (can the service take traffic? DB + Redis connected?)
/live    — alias for liveness (Kubernetes convention)

Used by:
- Docker healthcheck
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring (Prometheus blackbox exporter)
"""
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.db.redis import get_redis_client
from app.db.session import engine

router = APIRouter(tags=["Health"])

_start_time = time.time()


@router.get("/health")
async def health():
    """Basic liveness — if this returns, the process is alive."""
    return {
        "status": "healthy",
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@router.get("/ready")
async def ready():
    """
    Readiness check — validates DB and Redis connectivity.
    Returns 503 if either dependency is unavailable.
    """
    checks = {}
    overall = "ready"

    # Check PostgreSQL
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        overall = "not_ready"

    # Check Redis
    try:
        redis = get_redis_client()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        overall = "not_ready"

    status_code = 200 if overall == "ready" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )


@router.get("/live")
async def live():
    """Kubernetes liveness probe alias."""
    return {"status": "alive"}
