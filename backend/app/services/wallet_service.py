"""
Wallet Service — all wallet business logic.

Transfer fix: removed begin_nested() savepoint pattern which caused
"Can't operate on closed transaction" errors in SQLAlchemy 2.0 async.
All operations now happen in the single session-level transaction managed
by get_db(), committed once at the end.
"""
import json
import math
import uuid
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    AuthorizationException,
    ConflictException,
    DuplicateTransactionException,
    ExchangeRateUnavailableException,
    InsufficientFundsException,
    NotFoundException,
    WalletSuspendedException,
)
from app.models import Transfer, TransactionType, WalletStatus
from app.repositories.exchange_rate_repository import ExchangeRateRepository, IdempotencyRepository
from app.repositories.wallet_repository import TransactionRepository, WalletRepository
from app.schemas.wallet import (
    TransactionListResponse,
    TransactionResponse,
    TransferRequest,
    TransferResponse,
    WalletCreditRequest,
    WalletCreateRequest,
    WalletDebitRequest,
    WalletResponse,
)
from app.services.exchange_rate_service import ExchangeRateService

logger = structlog.get_logger(__name__)


class WalletService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.txn_repo = TransactionRepository(db)
        self.rate_repo = ExchangeRateRepository(db)
        self.idempotency_repo = IdempotencyRepository(db)
        self.rate_service = ExchangeRateService(db)

    # ── Create Wallet ─────────────────────────────────────────────────────────

    async def create_wallet(
        self, owner_id: uuid.UUID, request: WalletCreateRequest
    ) -> WalletResponse:
        existing = await self.wallet_repo.get_by_owner_and_currency(
            owner_id, request.currency
        )
        if existing:
            raise ConflictException(f"You already have a {request.currency} wallet.")

        wallet = await self.wallet_repo.create_wallet(
            owner_id=owner_id,
            currency=request.currency,
            label=request.label,
        )
        await self.db.commit()
        await self.db.refresh(wallet)
        logger.info("wallet_created", wallet_id=str(wallet.id), currency=wallet.currency)
        return WalletResponse.model_validate(wallet)

    # ── List Wallets ──────────────────────────────────────────────────────────

    async def get_user_wallets(self, owner_id: uuid.UUID) -> list[WalletResponse]:
        wallets = await self.wallet_repo.get_user_wallets(owner_id)
        return [WalletResponse.model_validate(w) for w in wallets]

    # ── Credit ────────────────────────────────────────────────────────────────

    async def credit_wallet(
        self, wallet_id: uuid.UUID, owner_id: uuid.UUID, request: WalletCreditRequest
    ) -> WalletResponse:
        wallet = await self.wallet_repo.get_by_id_with_lock(wallet_id)
        if not wallet:
            raise NotFoundException("Wallet", str(wallet_id))
        if wallet.owner_id != owner_id:
            raise AuthorizationException()
        if wallet.status != WalletStatus.ACTIVE:
            raise WalletSuspendedException(str(wallet_id))

        balance_before = wallet.balance
        new_balance = balance_before + request.amount

        await self.wallet_repo.update_balance(wallet, new_balance)
        await self.txn_repo.create_transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.CREDIT,
            amount=request.amount,
            currency=wallet.currency,
            balance_before=balance_before,
            balance_after=new_balance,
            description=request.description,
        )

        await self.db.commit()
        await self.db.refresh(wallet)
        logger.info("wallet_credited", wallet_id=str(wallet_id), amount=str(request.amount))
        return WalletResponse.model_validate(wallet)

    # ── Debit ─────────────────────────────────────────────────────────────────

    async def debit_wallet(
        self, wallet_id: uuid.UUID, owner_id: uuid.UUID, request: WalletDebitRequest
    ) -> WalletResponse:
        wallet = await self.wallet_repo.get_by_id_with_lock(wallet_id)
        if not wallet:
            raise NotFoundException("Wallet", str(wallet_id))
        if wallet.owner_id != owner_id:
            raise AuthorizationException()
        if wallet.status != WalletStatus.ACTIVE:
            raise WalletSuspendedException(str(wallet_id))
        if wallet.balance < request.amount:
            raise InsufficientFundsException(
                str(wallet.balance), str(request.amount), wallet.currency
            )

        balance_before = wallet.balance
        new_balance = balance_before - request.amount

        await self.wallet_repo.update_balance(wallet, new_balance)
        await self.txn_repo.create_transaction(
            wallet_id=wallet.id,
            transaction_type=TransactionType.DEBIT,
            amount=request.amount,
            currency=wallet.currency,
            balance_before=balance_before,
            balance_after=new_balance,
            description=request.description,
        )

        await self.db.commit()
        await self.db.refresh(wallet)
        logger.info("wallet_debited", wallet_id=str(wallet_id), amount=str(request.amount))
        return WalletResponse.model_validate(wallet)

    # ── Transfer ──────────────────────────────────────────────────────────────

    async def transfer(
        self,
        sender_id: uuid.UUID,
        request: TransferRequest,
        idempotency_key: str | None = None,
    ) -> TransferResponse:
        """
        Atomic transfer between two wallets.

        Locking order: always lock the wallet with the lower UUID first.
        This prevents deadlocks when two concurrent transfers involve the same pair.

        Exchange rate is fetched BEFORE acquiring locks to avoid holding
        a DB lock while making an external HTTP call.
        """

        # ── 1. Idempotency ────────────────────────────────────────────────────
        if idempotency_key:
            existing = await self.idempotency_repo.get_by_key(idempotency_key)
            if existing:
                raise DuplicateTransactionException(idempotency_key)

        # ── 2. Validate sender owns the sender wallet ─────────────────────────
        sender_wallet_peek = await self.wallet_repo.get_by_id(request.sender_wallet_id)
        if not sender_wallet_peek:
            raise NotFoundException("Sender wallet", str(request.sender_wallet_id))
        if sender_wallet_peek.owner_id != sender_id:
            raise AuthorizationException("Sender wallet does not belong to you.")
        if sender_wallet_peek.status != WalletStatus.ACTIVE:
            raise WalletSuspendedException(str(request.sender_wallet_id))

        # ── 3. Validate recipient wallet ──────────────────────────────────────
        if request.sender_wallet_id == request.recipient_wallet_id:
            raise ConflictException("Cannot transfer to the same wallet.")

        recipient_peek = await self.wallet_repo.get_by_id(request.recipient_wallet_id)
        if not recipient_peek:
            raise NotFoundException("Recipient wallet", str(request.recipient_wallet_id))
        if recipient_peek.status != WalletStatus.ACTIVE:
            raise WalletSuspendedException(str(request.recipient_wallet_id))

        # ── 4. Fetch exchange rate BEFORE locking ─────────────────────────────
        exchange_rate: Decimal | None = None
        converted_amount = request.amount

        if sender_wallet_peek.currency != recipient_peek.currency:
            try:
                exchange_rate = await self.rate_service.get_rate(
                    sender_wallet_peek.currency,
                    recipient_peek.currency,
                )
                converted_amount = (request.amount * exchange_rate).quantize(
                    Decimal("0.00000001")
                )
                logger.info(
                    "cross_currency_transfer",
                    from_currency=sender_wallet_peek.currency,
                    to_currency=recipient_peek.currency,
                    rate=str(exchange_rate),
                )
            except Exception as exc:
                raise ExchangeRateUnavailableException(
                    sender_wallet_peek.currency, recipient_peek.currency
                ) from exc

        # ── 5. Acquire row locks (lower UUID first = deadlock prevention) ─────
        id_a, id_b = sorted(
            [request.sender_wallet_id, request.recipient_wallet_id]
        )
        locked_a = await self.wallet_repo.get_by_id_with_lock(id_a)
        locked_b = await self.wallet_repo.get_by_id_with_lock(id_b)

        sender_wallet = locked_a if locked_a.id == request.sender_wallet_id else locked_b
        recipient_wallet = locked_b if locked_b.id == request.recipient_wallet_id else locked_a

        # ── 6. Balance check ──────────────────────────────────────────────────
        if sender_wallet.balance < request.amount:
            raise InsufficientFundsException(
                str(sender_wallet.balance),
                str(request.amount),
                sender_wallet.currency,
            )

        # ── 7. Apply balance changes ──────────────────────────────────────────
        sender_before = sender_wallet.balance
        recipient_before = recipient_wallet.balance
        sender_after = sender_before - request.amount
        recipient_after = recipient_before + converted_amount

        await self.wallet_repo.update_balance(sender_wallet, sender_after)
        await self.wallet_repo.update_balance(recipient_wallet, recipient_after)

        # ── 8. Transaction records ────────────────────────────────────────────
        ref = str(uuid.uuid4())

        await self.txn_repo.create_transaction(
            wallet_id=sender_wallet.id,
            transaction_type=TransactionType.TRANSFER,
            amount=request.amount,
            currency=sender_wallet.currency,
            balance_before=sender_before,
            balance_after=sender_after,
            reference=ref,
            description=request.note,
        )
        await self.txn_repo.create_transaction(
            wallet_id=recipient_wallet.id,
            transaction_type=TransactionType.TRANSFER,
            amount=converted_amount,
            currency=recipient_wallet.currency,
            balance_before=recipient_before,
            balance_after=recipient_after,
            reference=ref,
            description=request.note,
        )

        # ── 9. Transfer record ────────────────────────────────────────────────
        transfer = Transfer(
            sender_wallet_id=sender_wallet.id,
            recipient_wallet_id=recipient_wallet.id,
            amount=request.amount,
            currency=sender_wallet.currency,
            exchange_rate=exchange_rate,
            converted_amount=converted_amount,
            note=request.note,
            idempotency_key=idempotency_key,
        )
        self.db.add(transfer)
        await self.db.flush()

        # ── 10. Save idempotency key ──────────────────────────────────────────
        if idempotency_key:
            await self.idempotency_repo.create(
                key=idempotency_key,
                user_id=sender_id,
                request_path="/api/v1/wallets/transfer",
                response_status=201,
                response_body=json.dumps({"transfer_id": str(transfer.id)}),
            )

        # ── 11. Single commit — atomic ────────────────────────────────────────
        await self.db.commit()
        await self.db.refresh(transfer)

        logger.info(
            "transfer_completed",
            ref=ref,
            sender=str(sender_wallet.id),
            recipient=str(recipient_wallet.id),
            amount=str(request.amount),
        )
        return TransferResponse.model_validate(transfer)

    # ── Transaction History ───────────────────────────────────────────────────

    async def get_transaction_history(
        self,
        wallet_id: uuid.UUID,
        owner_id: uuid.UUID,
        transaction_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> TransactionListResponse:
        wallet = await self.wallet_repo.get_by_id(wallet_id)
        if not wallet:
            raise NotFoundException("Wallet", str(wallet_id))
        if wallet.owner_id != owner_id:
            raise AuthorizationException()

        txn_type = None
        if transaction_type:
            try:
                txn_type = TransactionType(transaction_type)
            except ValueError:
                pass

        items, total = await self.txn_repo.get_wallet_transactions(
            wallet_id=wallet_id,
            transaction_type=txn_type,
            page=page,
            page_size=page_size,
        )

        return TransactionListResponse(
            items=[TransactionResponse.model_validate(t) for t in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total > 0 else 1,
        )
