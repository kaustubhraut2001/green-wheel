"""
Exchange Rate Provider — Adapter Pattern.

The Adapter Pattern decouples the application from specific third-party APIs.
Adding a new exchange rate provider = adding a new adapter class, zero changes elsewhere.

Abstract interface → multiple concrete adapters
ExchangeRateProvider (ABC)
├── OpenExchangeAdapter
├── FixerAdapter
└── CurrencyLayerAdapter

The factory function selects the adapter based on configuration.
"""
import asyncio
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict

import httpx
import structlog

from app.core.config import settings
from app.exceptions import ExchangeRateUnavailableException

logger = structlog.get_logger(__name__)


class ExchangeRateProvider(ABC):
    """Abstract interface that all exchange rate adapters must implement."""

    @abstractmethod
    async def get_rates(self, base_currency: str) -> Dict[str, Decimal]:
        """
        Fetch exchange rates for a base currency.
        Returns a dict of {target_currency: rate}.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        raise NotImplementedError


class OpenExchangeAdapter(ExchangeRateProvider):
    """
    Adapter for openexchangerates.org.
    Free tier supports USD as base only.
    """

    BASE_URL = "https://openexchangerates.org/api"

    def __init__(self, app_id: str):
        self.app_id = app_id
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_rates(self, base_currency: str = "USD") -> Dict[str, Decimal]:
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/latest.json",
                params={"app_id": self.app_id, "base": base_currency},
            )
            resp.raise_for_status()
            data = resp.json()
            return {k: Decimal(str(v)) for k, v in data.get("rates", {}).items()}
        except Exception as exc:
            logger.error("open_exchange_fetch_failed", error=str(exc))
            raise ExchangeRateUnavailableException(base_currency, "ALL") from exc

    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        rates = await self.get_rates(base_currency)
        rate = rates.get(target_currency.upper())
        if rate is None:
            raise ExchangeRateUnavailableException(base_currency, target_currency)
        return rate


class FixerAdapter(ExchangeRateProvider):
    """Adapter for fixer.io."""

    BASE_URL = "https://data.fixer.io/api"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def get_rates(self, base_currency: str = "EUR") -> Dict[str, Decimal]:
        try:
            resp = await self._client.get(
                f"{self.BASE_URL}/latest",
                params={"access_key": self.api_key, "base": base_currency},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                raise Exception(data.get("error", {}).get("info", "Unknown fixer error"))
            return {k: Decimal(str(v)) for k, v in data.get("rates", {}).items()}
        except Exception as exc:
            logger.error("fixer_fetch_failed", error=str(exc))
            raise ExchangeRateUnavailableException(base_currency, "ALL") from exc

    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        rates = await self.get_rates(base_currency)
        rate = rates.get(target_currency.upper())
        if rate is None:
            raise ExchangeRateUnavailableException(base_currency, target_currency)
        return rate


class MockExchangeAdapter(ExchangeRateProvider):
    """
    Mock adapter for tests and development.
    Returns deterministic rates — no external network calls.
    """

    MOCK_RATES = {
        "USD": {"EUR": Decimal("0.92"), "GBP": Decimal("0.79"), "NGN": Decimal("1500"), "INR": Decimal("83.5"), "JPY": Decimal("149")},
        "EUR": {"USD": Decimal("1.09"), "GBP": Decimal("0.86")},
        "GBP": {"USD": Decimal("1.27"), "EUR": Decimal("1.16")},
    }

    async def get_rates(self, base_currency: str) -> Dict[str, Decimal]:
        return self.MOCK_RATES.get(base_currency.upper(), {})

    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        rates = await self.get_rates(base_currency)
        rate = rates.get(target_currency.upper())
        if rate is None:
            raise ExchangeRateUnavailableException(base_currency, target_currency)
        return rate


def get_exchange_rate_provider() -> ExchangeRateProvider:
    """
    Factory function — selects provider based on configuration.
    This is the single place where provider coupling exists.
    """
    provider = settings.EXCHANGE_RATE_PROVIDER.lower()

    if provider == "open_exchange":
        if not settings.OPEN_EXCHANGE_APP_ID:
            logger.warning("No Open Exchange API key, falling back to mock provider")
            return MockExchangeAdapter()
        return OpenExchangeAdapter(app_id=settings.OPEN_EXCHANGE_APP_ID)

    elif provider == "fixer":
        if not settings.FIXER_API_KEY:
            logger.warning("No Fixer API key, falling back to mock provider")
            return MockExchangeAdapter()
        return FixerAdapter(api_key=settings.FIXER_API_KEY)

    else:
        logger.info("Using mock exchange rate provider")
        return MockExchangeAdapter()
