"""
SQLAlchemy ORM Models.

Relationships are explicitly declared so SQLAlchemy can eager-load them
when needed without N+1 queries.
"""
import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


# ── Enumerations ──────────────────────────────────────────────────────────────

class TransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    CONVERSION = "conversion"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class WalletStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)

    # Relationships
    wallets: Mapped[list["Wallet"]] = relationship("Wallet", back_populates="owner", lazy="select")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user")


# ── Refresh Token ─────────────────────────────────────────────────────────────

class RefreshToken(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[str] = mapped_column(String(50), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")


# ── Wallet ────────────────────────────────────────────────────────────────────

class Wallet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("owner_id", "currency", name="uq_wallet_owner_currency"),
        Index("ix_wallet_owner_id", "owner_id"),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Numeric(18, 8) supports currencies with up to 8 decimal places (e.g. crypto)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=Decimal("0"), nullable=False)
    status: Mapped[WalletStatus] = mapped_column(Enum(WalletStatus, native_enum=False), default=WalletStatus.ACTIVE, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="wallets")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="wallet", foreign_keys="Transaction.wallet_id")


# ── Transaction ───────────────────────────────────────────────────────────────

class Transaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transaction_wallet_id", "wallet_id"),
        Index("ix_transaction_created_at", "created_at"),
        Index("ix_transaction_type", "transaction_type"),
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, native_enum=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus, native_enum=False), default=TransactionStatus.COMPLETED, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for extensibility

    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions", foreign_keys=[wallet_id])


# ── Transfer ──────────────────────────────────────────────────────────────────

class Transfer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transfers"

    sender_wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    recipient_wallet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    converted_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus, native_enum=False), default=TransactionStatus.COMPLETED, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    sender_wallet: Mapped["Wallet"] = relationship("Wallet", foreign_keys=[sender_wallet_id])
    recipient_wallet: Mapped["Wallet"] = relationship("Wallet", foreign_keys=[recipient_wallet_id])


# ── Exchange Rate ─────────────────────────────────────────────────────────────

class ExchangeRate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("base_currency", "target_currency", "provider", name="uq_rate_pair_provider"),
        Index("ix_exchange_rate_pair", "base_currency", "target_currency"),
    )

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)


# ── Idempotency Key ───────────────────────────────────────────────────────────

class IdempotencyKey(Base, UUIDMixin, TimestampMixin):
    """
    Prevents duplicate processing of the same request.
    The response_body is stored so we can return the exact same result
    for duplicate requests without re-processing.
    """
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    response_status: Mapped[int] = mapped_column(nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(Base, UUIDMixin, TimestampMixin):
    """
    Immutable audit trail for all sensitive operations.
    Never delete or update rows in this table.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_action", "action"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
