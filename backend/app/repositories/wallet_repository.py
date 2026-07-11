"""
Wallet Repository.

Uses SELECT ... FOR UPDATE (pessimistic locking) when modifying balances.

Why pessimistic locking?
In payment systems, concurrent updates to the same wallet row must be serialised.
Optimistic locking (version column) causes cascading retries under high contention
and makes retry logic complex when side effects (notifications, audit logs) exist.
Pessimistic locking holds the row lock for the duration of the transaction
(milliseconds), serialising updates safely without application-level retry logic.
"""
import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionType, Wallet, WalletStatus
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, db: AsyncSession):
        super().__init__(Wallet, db)

    async def get_by_id(self, wallet_id: uuid.UUID) -> Optional[Wallet]:
        """Fetch wallet without locking — use for read-only checks."""
        result = await self.db.execute(
            select(Wallet).where(Wallet.id == wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_lock(self, wallet_id: uuid.UUID) -> Optional[Wallet]:
        """
        Fetch wallet with SELECT FOR UPDATE row lock.
        Must be called inside an active transaction.
        Blocks concurrent writers until this transaction commits or rolls back.
        """
        result = await self.db.execute(
            select(Wallet)
            .where(Wallet.id == wallet_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_user_wallets(self, owner_id: uuid.UUID) -> List[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(Wallet.owner_id == owner_id)
        )
        return list(result.scalars().all())

    async def get_by_owner_and_currency(
        self, owner_id: uuid.UUID, currency: str
    ) -> Optional[Wallet]:
        result = await self.db.execute(
            select(Wallet).where(
                Wallet.owner_id == owner_id,
                Wallet.currency == currency.upper(),
            )
        )
        return result.scalar_one_or_none()

    async def create_wallet(
        self, owner_id: uuid.UUID, currency: str, label: Optional[str] = None
    ) -> Wallet:
        wallet = Wallet(
            owner_id=owner_id,
            currency=currency.upper(),
            balance=Decimal("0"),
            status=WalletStatus.ACTIVE,
            label=label,
        )
        return await self.save(wallet)

    async def update_balance(self, wallet: Wallet, new_balance: Decimal) -> Wallet:
        """
        Update wallet balance in place.
        The wallet object must already be loaded in the current session
        (obtained via get_by_id_with_lock to ensure row lock is held).
        """
        wallet.balance = new_balance
        await self.db.flush()
        return wallet


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def create_transaction(
        self,
        wallet_id: uuid.UUID,
        transaction_type: TransactionType,
        amount: Decimal,
        currency: str,
        balance_before: Decimal,
        balance_after: Decimal,
        reference: Optional[str] = None,
        description: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Transaction:
        txn = Transaction(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            amount=amount,
            currency=currency,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description=description,
            metadata_json=metadata_json,
        )
        self.db.add(txn)
        await self.db.flush()
        return txn

    async def get_wallet_transactions(
        self,
        wallet_id: uuid.UUID,
        transaction_type: Optional[TransactionType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Transaction], int]:
        base_filter = [Transaction.wallet_id == wallet_id]
        if transaction_type:
            base_filter.append(Transaction.transaction_type == transaction_type)

        count_result = await self.db.execute(
            select(func.count()).select_from(Transaction).where(*base_filter)
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(Transaction)
            .where(*base_filter)
            .order_by(Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total
