"""
Exchange Rate Repository + Idempotency Repository.
"""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExchangeRate, IdempotencyKey
from app.repositories.base import BaseRepository


class ExchangeRateRepository(BaseRepository[ExchangeRate]):
    def __init__(self, db: AsyncSession):
        super().__init__(ExchangeRate, db)

    async def get_rate(
        self, base_currency: str, target_currency: str
    ) -> Optional[ExchangeRate]:
        result = await self.db.execute(
            select(ExchangeRate).where(
                ExchangeRate.base_currency == base_currency.upper(),
                ExchangeRate.target_currency == target_currency.upper(),
            )
        )
        return result.scalar_one_or_none()

    async def upsert_rate(
        self,
        base_currency: str,
        target_currency: str,
        rate: Decimal,
        provider: str,
    ) -> ExchangeRate:
        existing = await self.get_rate(base_currency, target_currency)
        if existing:
            existing.rate = rate
            existing.provider = provider
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        new_rate = ExchangeRate(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            rate=rate,
            provider=provider,
        )
        return await self.save(new_rate)


class IdempotencyRepository(BaseRepository[IdempotencyKey]):
    def __init__(self, db: AsyncSession):
        super().__init__(IdempotencyKey, db)

    async def get_by_key(self, key: str) -> Optional[IdempotencyKey]:
        result = await self.db.execute(
            select(IdempotencyKey).where(IdempotencyKey.key == key)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        key: str,
        user_id: uuid.UUID,
        request_path: str,
        response_status: int,
        response_body: str,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            key=key,
            user_id=user_id,
            request_path=request_path,
            response_status=response_status,
            response_body=response_body,
        )
        return await self.save(record)
