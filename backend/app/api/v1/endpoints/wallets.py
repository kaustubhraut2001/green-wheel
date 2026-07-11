"""
Wallet endpoints — create, credit, debit, transfer, history.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, get_idempotency_key
from app.models import User
from app.schemas.wallet import (
    TransactionListResponse,
    TransferRequest,
    TransferResponse,
    WalletCreditRequest,
    WalletCreateRequest,
    WalletDebitRequest,
    WalletResponse,
)
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    request: WalletCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new currency wallet for the authenticated user."""
    service = WalletService(db)
    return await service.create_wallet(current_user.id, request)


@router.get("", response_model=list[WalletResponse])
async def list_wallets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all wallets belonging to the authenticated user."""
    service = WalletService(db)
    return await service.get_user_wallets(current_user.id)


@router.post("/{wallet_id}/credit", response_model=WalletResponse)
async def credit_wallet(
    wallet_id: uuid.UUID,
    request: WalletCreditRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add funds to a wallet."""
    service = WalletService(db)
    return await service.credit_wallet(wallet_id, current_user.id, request)


@router.post("/{wallet_id}/debit", response_model=WalletResponse)
async def debit_wallet(
    wallet_id: uuid.UUID,
    request: WalletDebitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove funds from a wallet."""
    service = WalletService(db)
    return await service.debit_wallet(wallet_id, current_user.id, request)


@router.post("/transfer", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def transfer(
    request: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
):
    """
    Transfer funds to another user's wallet.
    Include Idempotency-Key header to prevent duplicate transfers.
    Supports cross-currency transfers with live exchange rates.
    """
    service = WalletService(db)
    return await service.transfer(current_user.id, request, idempotency_key)


@router.get("/{wallet_id}/transactions", response_model=TransactionListResponse)
async def transaction_history(
    wallet_id: uuid.UUID,
    transaction_type: Optional[str] = Query(default=None, description="Filter: credit, debit, transfer, conversion"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Paginated transaction history for a wallet with optional type filter."""
    service = WalletService(db)
    return await service.get_transaction_history(
        wallet_id=wallet_id,
        owner_id=current_user.id,
        transaction_type=transaction_type,
        page=page,
        page_size=page_size,
    )
