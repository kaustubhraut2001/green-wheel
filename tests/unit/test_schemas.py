"""
Unit tests for Pydantic schemas — validation logic.
"""
import pytest
from pydantic import ValidationError

from app.schemas.user import UserRegisterRequest
from app.schemas.wallet import WalletCreditRequest, WalletDebitRequest, TransferRequest
from decimal import Decimal
import uuid


@pytest.mark.unit
class TestUserRegisterSchema:
    def test_valid_registration(self):
        data = UserRegisterRequest(
            email="valid@example.com",
            password="Strong@123",
            first_name="John",
            last_name="Doe",
            default_currency="USD",
        )
        assert data.email == "valid@example.com"
        assert data.default_currency == "USD"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError, match="Password must be"):
            UserRegisterRequest(
                email="test@example.com",
                password="weakpassword",
                first_name="A",
                last_name="B",
            )

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserRegisterRequest(
                email="not-an-email",
                password="Strong@123",
                first_name="A",
                last_name="B",
            )

    def test_unsupported_currency_rejected(self):
        with pytest.raises(ValidationError, match="Unsupported currency"):
            UserRegisterRequest(
                email="test@example.com",
                password="Strong@123",
                first_name="A",
                last_name="B",
                default_currency="XYZ",
            )

    def test_currency_normalised_to_uppercase(self):
        data = UserRegisterRequest(
            email="test@example.com",
            password="Strong@123",
            first_name="A",
            last_name="B",
            default_currency="usd",
        )
        assert data.default_currency == "USD"


@pytest.mark.unit
class TestWalletSchemas:
    def test_credit_amount_must_be_positive(self):
        with pytest.raises(ValidationError):
            WalletCreditRequest(amount=Decimal("-10"))

    def test_credit_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            WalletCreditRequest(amount=Decimal("0"))

    def test_debit_amount_must_be_positive(self):
        with pytest.raises(ValidationError):
            WalletDebitRequest(amount=Decimal("-1"))

    def test_valid_credit(self):
        req = WalletCreditRequest(amount=Decimal("100.50"))
        assert req.amount == Decimal("100.50")

    def test_transfer_requires_valid_uuid(self):
        with pytest.raises(ValidationError):
            from app.schemas.wallet import TransferRequest
            TransferRequest(recipient_wallet_id="not-a-uuid", amount=Decimal("10"))
