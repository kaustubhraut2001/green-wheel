"""
Pydantic V2 schemas for Wallets and Transactions.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models import TransactionType, TransactionStatus, WalletStatus

SUPPORTED_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF",
    "CNY", "INR", "NGN", "GHS", "KES", "ZAR",
}


class WalletCreateRequest(BaseModel):
    currency: str = Field(..., max_length=3)
    label: Optional[str] = Field(None, max_length=100)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(f"Unsupported currency: {v}")
        return v


class WalletResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    currency: str
    balance: Decimal
    status: WalletStatus
    label: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletCreditRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)


class WalletDebitRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)


class TransferRequest(BaseModel):
    sender_wallet_id: uuid.UUID           # which of the sender's wallets to debit
    recipient_wallet_id: uuid.UUID        # target wallet
    amount: Decimal = Field(..., gt=0)
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class ConversionRequest(BaseModel):
    from_wallet_id: uuid.UUID
    to_wallet_id: uuid.UUID
    amount: Decimal = Field(..., gt=0)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    wallet_id: uuid.UUID
    transaction_type: TransactionType
    amount: Decimal
    currency: str
    balance_before: Decimal
    balance_after: Decimal
    status: TransactionStatus
    reference: Optional[str]
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TransferResponse(BaseModel):
    id: uuid.UUID
    sender_wallet_id: uuid.UUID
    recipient_wallet_id: uuid.UUID
    amount: Decimal
    currency: str
    exchange_rate: Optional[Decimal]
    converted_amount: Optional[Decimal]
    status: TransactionStatus
    note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ExchangeRateResponse(BaseModel):
    base_currency: str
    target_currency: str
    rate: Decimal
    provider: str
    updated_at: datetime

    model_config = {"from_attributes": True}
