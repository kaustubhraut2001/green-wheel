"""
Circuit Breaker implementation for external service calls.

Pattern: Closed → (failures exceed threshold) → Open → (timeout elapses) → Half-Open → (success) → Closed
                                                                                        → (failure)  → Open

Why Circuit Breaker for exchange rates?
- External providers go down. Without a circuit breaker, every request
  hangs for the HTTP timeout (10s+), exhausting the thread pool.
- Circuit breaker fails fast, returns cached rates, and retries provider
  automatically after the recovery window.

Implementation uses Redis so circuit state is shared across all app instances.
"""
import time
from enum import Enum
from typing import Callable, TypeVar

import structlog

from app.core.config import settings
from app.db.redis import get_redis_client

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing — reject requests immediately
    HALF_OPEN = "half_open"  # Testing recovery — allow one probe request


class CircuitBreaker:
    """
    Redis-backed circuit breaker.
    State and failure counts are stored in Redis so all replicas share state.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = None,
        recovery_timeout: int = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold or settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT

    @property
    def _state_key(self) -> str:
        return f"circuit_breaker:{self.name}:state"

    @property
    def _failure_key(self) -> str:
        return f"circuit_breaker:{self.name}:failures"

    @property
    def _opened_at_key(self) -> str:
        return f"circuit_breaker:{self.name}:opened_at"

    async def get_state(self) -> CircuitState:
        redis = get_redis_client()
        state = await redis.get(self._state_key)

        if state is None or state == CircuitState.CLOSED:
            return CircuitState.CLOSED

        if state == CircuitState.OPEN:
            opened_at = await redis.get(self._opened_at_key)
            if opened_at and (time.time() - float(opened_at)) > self.recovery_timeout:
                # Transition to half-open to probe recovery
                await redis.set(self._state_key, CircuitState.HALF_OPEN)
                logger.info("circuit_breaker_half_open", name=self.name)
                return CircuitState.HALF_OPEN

        return CircuitState(state)

    async def record_failure(self) -> None:
        redis = get_redis_client()
        failures = await redis.incr(self._failure_key)
        await redis.expire(self._failure_key, self.recovery_timeout * 2)

        if failures >= self.failure_threshold:
            await redis.set(self._state_key, CircuitState.OPEN)
            await redis.set(self._opened_at_key, str(time.time()))
            logger.warning(
                "circuit_breaker_opened",
                name=self.name,
                failures=failures,
                threshold=self.failure_threshold,
            )

    async def record_success(self) -> None:
        redis = get_redis_client()
        await redis.delete(self._state_key)
        await redis.delete(self._failure_key)
        await redis.delete(self._opened_at_key)
        logger.info("circuit_breaker_closed", name=self.name)

    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute func if circuit is closed/half-open.
        Raises CircuitOpenException if the circuit is open.
        """
        from app.exceptions import CircuitOpenException

        state = await self.get_state()

        if state == CircuitState.OPEN:
            logger.warning("circuit_breaker_rejected", name=self.name)
            raise CircuitOpenException(self.name)

        try:
            result = await func(*args, **kwargs)
            if state == CircuitState.HALF_OPEN:
                await self.record_success()
            return result
        except Exception as exc:
            await self.record_failure()
            raise


# Module-level singleton — shared across all requests in this process
exchange_rate_circuit_breaker = CircuitBreaker(name="exchange_rate_provider")
