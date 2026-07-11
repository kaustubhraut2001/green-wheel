"""
Exchange rate endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, require_admin
from app.models import User
from app.schemas.wallet import ExchangeRateResponse
from app.services.exchange_rate_service import ExchangeRateService
from app.workers.tasks import refresh_exchange_rates_task

router = APIRouter(prefix="/exchange-rates", tags=["Exchange Rates"])


@router.get("", response_model=list[ExchangeRateResponse])
async def get_rates(
    base: str = Query(default="USD", description="Base currency code"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get all exchange rates for a given base currency."""
    service = ExchangeRateService(db)
    return await service.get_all_rates(base)


@router.get("/{base}/{target}", response_model=dict)
async def get_single_rate(
    base: str,
    target: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get the exchange rate for a specific currency pair."""
    service = ExchangeRateService(db)
    rate = await service.get_rate(base, target)
    return {"base": base.upper(), "target": target.upper(), "rate": str(rate)}


@router.post("/refresh", status_code=202)
async def trigger_refresh(
    _: User = Depends(require_admin),
):
    """
    Manually trigger exchange rate refresh (admin only).
    Runs as a Celery background task — returns immediately.
    """
    refresh_exchange_rates_task.delay()
    return {"message": "Exchange rate refresh queued.", "status": "accepted"}
