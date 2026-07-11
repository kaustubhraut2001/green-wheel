"""
Unit tests for WalletService business logic.
"""
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import (
    ConflictException,
    InsufficientFundsException,
    WalletSuspendedException,
)
from app.models import WalletStatus
from app.schemas.wallet import WalletCreditRequest, WalletDebitRequest, WalletCreateRequest


@pytest.mark.unit
class TestWalletCredit:
    @pytest.mark.asyncio
    async def test_credit_increases_balance(self, db_session):
        """Crediting a wallet increases balance by the exact amount."""
        owner_id = uuid.uuid4()
        wallet_id = uuid.uuid4()

        from app.models import Wallet
        fake_wallet = MagicMock(spec=Wallet)
        fake_wallet.id = wallet_id
        fake_wallet.owner_id = owner_id
        fake_wallet.currency = "USD"
        fake_wallet.balance = Decimal("100.00")
        fake_wallet.status = WalletStatus.ACTIVE

        with patch("app.services.wallet_service.WalletRepository") as MockWR, \
             patch("app.services.wallet_service.TransactionRepository") as MockTR, \
             patch("app.services.wallet_service.ExchangeRateRepository"), \
             patch("app.services.wallet_service.IdempotencyRepository"), \
             patch("app.services.wallet_service.ExchangeRateService"), \
             patch("app.services.wallet_service.get_redis_client"):

            mock_wr = MockWR.return_value
            mock_wr.get_by_id_with_lock = AsyncMock(return_value=fake_wallet)
            mock_wr.update_balance = AsyncMock(return_value=fake_wallet)

            mock_tr = MockTR.return_value
            mock_tr.create_transaction = AsyncMock()

            db_session.begin_nested = MagicMock()
            db_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
            db_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=False)
            db_session.commit = AsyncMock()

            from app.services.wallet_service import WalletService
            service = WalletService(db_session)
            request = WalletCreditRequest(amount=Decimal("50.00"))

            await service.credit_wallet(wallet_id, owner_id, request)

            # Verify update_balance was called with correct new balance
            mock_wr.update_balance.assert_called_once_with(fake_wallet, Decimal("150.00"))

    @pytest.mark.asyncio
    async def test_debit_insufficient_funds_raises(self, db_session):
        """Debiting more than balance raises InsufficientFundsException."""
        owner_id = uuid.uuid4()
        wallet_id = uuid.uuid4()

        from app.models import Wallet
        fake_wallet = MagicMock(spec=Wallet)
        fake_wallet.id = wallet_id
        fake_wallet.owner_id = owner_id
        fake_wallet.currency = "USD"
        fake_wallet.balance = Decimal("10.00")
        fake_wallet.status = WalletStatus.ACTIVE

        with patch("app.services.wallet_service.WalletRepository") as MockWR, \
             patch("app.services.wallet_service.TransactionRepository"), \
             patch("app.services.wallet_service.ExchangeRateRepository"), \
             patch("app.services.wallet_service.IdempotencyRepository"), \
             patch("app.services.wallet_service.ExchangeRateService"), \
             patch("app.services.wallet_service.get_redis_client"):

            mock_wr = MockWR.return_value
            mock_wr.get_by_id_with_lock = AsyncMock(return_value=fake_wallet)

            db_session.begin_nested = MagicMock()
            db_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
            db_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.wallet_service import WalletService
            service = WalletService(db_session)

            with pytest.raises(InsufficientFundsException):
                await service.debit_wallet(
                    wallet_id, owner_id, WalletDebitRequest(amount=Decimal("50.00"))
                )

    @pytest.mark.asyncio
    async def test_credit_suspended_wallet_raises(self, db_session):
        """Crediting a suspended wallet raises WalletSuspendedException."""
        owner_id = uuid.uuid4()
        wallet_id = uuid.uuid4()

        from app.models import Wallet
        fake_wallet = MagicMock(spec=Wallet)
        fake_wallet.id = wallet_id
        fake_wallet.owner_id = owner_id
        fake_wallet.currency = "USD"
        fake_wallet.balance = Decimal("100.00")
        fake_wallet.status = WalletStatus.SUSPENDED

        with patch("app.services.wallet_service.WalletRepository") as MockWR, \
             patch("app.services.wallet_service.TransactionRepository"), \
             patch("app.services.wallet_service.ExchangeRateRepository"), \
             patch("app.services.wallet_service.IdempotencyRepository"), \
             patch("app.services.wallet_service.ExchangeRateService"), \
             patch("app.services.wallet_service.get_redis_client"):

            mock_wr = MockWR.return_value
            mock_wr.get_by_id_with_lock = AsyncMock(return_value=fake_wallet)

            db_session.begin_nested = MagicMock()
            db_session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
            db_session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.wallet_service import WalletService
            service = WalletService(db_session)

            with pytest.raises(WalletSuspendedException):
                await service.credit_wallet(
                    wallet_id, owner_id, WalletCreditRequest(amount=Decimal("10.00"))
                )


@pytest.mark.unit
class TestWalletCreation:
    @pytest.mark.asyncio
    async def test_duplicate_currency_wallet_raises_conflict(self, db_session):
        """Creating a wallet for a currency already owned raises ConflictException."""
        owner_id = uuid.uuid4()

        from app.models import Wallet
        existing_wallet = MagicMock(spec=Wallet)

        with patch("app.services.wallet_service.WalletRepository") as MockWR, \
             patch("app.services.wallet_service.TransactionRepository"), \
             patch("app.services.wallet_service.ExchangeRateRepository"), \
             patch("app.services.wallet_service.IdempotencyRepository"), \
             patch("app.services.wallet_service.ExchangeRateService"), \
             patch("app.services.wallet_service.get_redis_client"):

            mock_wr = MockWR.return_value
            mock_wr.get_by_owner_and_currency = AsyncMock(return_value=existing_wallet)

            from app.services.wallet_service import WalletService
            service = WalletService(db_session)

            with pytest.raises(ConflictException):
                await service.create_wallet(
                    owner_id, WalletCreateRequest(currency="USD")
                )
