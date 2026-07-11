"""
Exchange Rate Service.

Cache strategy:
1. Check Redis (fast, sub-millisecond)
2. Check PostgreSQL (persisted rates from last refresh)
3. Call provider via circuit breaker (external HTTP)
4. Store in Redis + DB for future requests

This layered approach means the system continues serving rates
even when the external provider is down (uses last known good rates).
"""
import json
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.circuit_breaker import exchange_rate_circuit_breaker
from app.adapters.exchange_rate import get_exchange_rate_provider
from app.core.config import settings
from app.db.redis import get_redis_client
from app.exceptions import ExchangeRateUnavailableException
from app.repositories.exchange_rate_repository import ExchangeRateRepository
from app.schemas.wallet import ExchangeRateResponse

logger = structlog.get_logger(__name__)


class ExchangeRateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rate_repo = ExchangeRateRepository(db)
        self.provider = get_exchange_rate_provider()
        self.redis = get_redis_client()

    def _cache_key(self, base: str, target: str) -> str:
        return f"exchange_rate:{base.upper()}:{target.upper()}"

    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        """Return exchange rate with Redis → DB → Provider fallback chain."""
        base = base_currency.upper()
        target = target_currency.upper()

        if base == target:
            return Decimal("1")

        # 1. Redis cache
        cached = await self.redis.get(self._cache_key(base, target))
        if cached:
            logger.debug("exchange_rate_cache_hit", base=base, target=target)
            return Decimal(cached)

        # 2. DB
        db_rate = await self.rate_repo.get_rate(base, target)
        if db_rate:
            await self.redis.setex(
                self._cache_key(base, target),
                settings.EXCHANGE_RATE_CACHE_TTL,
                str(db_rate.rate),
            )
            return db_rate.rate

        # 3. Provider (via circuit breaker)
        try:
            rate = await exchange_rate_circuit_breaker.call(
                self.provider.get_rate, base, target
            )
            await self._persist_rate(base, target, rate)
            return rate
        except Exception as exc:
            logger.error("exchange_rate_fetch_failed", base=base, target=target, error=str(exc))
            raise ExchangeRateUnavailableException(base, target) from exc

    async def _persist_rate(self, base: str, target: str, rate: Decimal) -> None:
        """Cache in Redis and upsert in DB."""
        await self.redis.setex(
            self._cache_key(base, target),
            settings.EXCHANGE_RATE_CACHE_TTL,
            str(rate),
        )
        provider_name = settings.EXCHANGE_RATE_PROVIDER
        await self.rate_repo.upsert_rate(base, target, rate, provider_name)
        await self.db.commit()

    async def refresh_all_rates(self) -> dict:
        """
        Bulk-refresh rates from provider.
        Called by Celery worker on a schedule.
        """
        try:
            rates = await exchange_rate_circuit_breaker.call(
                self.provider.get_rates, "USD"
            )
            saved = 0
            for target, rate in rates.items():
                try:
                    await self._persist_rate("USD", target, rate)
                    saved += 1
                except Exception:
                    pass
            logger.info("exchange_rates_refreshed", count=saved)
            return {"refreshed": saved, "base": "USD"}
        except Exception as exc:
            logger.error("exchange_rate_refresh_failed", error=str(exc))
            raise

    async def get_all_rates(self, base_currency: str) -> list[ExchangeRateResponse]:
        from sqlalchemy import select
        from app.models import ExchangeRate
        result = await self.db.execute(
            select(ExchangeRate).where(ExchangeRate.base_currency == base_currency.upper())
        )
        return [ExchangeRateResponse.model_validate(r) for r in result.scalars().all()]
