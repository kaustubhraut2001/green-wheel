"""
Exchange Rate Provider — Adapter Pattern.

Fix: Cross-rate calculation so ANY currency pair works.
If USD→JPY is known and USD→EUR is known, we can derive EUR→JPY = (USD→JPY) / (USD→EUR).
This eliminates "exchange rate unavailable" for pairs not directly provided by the API.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional

import httpx
import structlog

from app.core.config import settings
from app.exceptions import ExchangeRateUnavailableException

logger = structlog.get_logger(__name__)


class ExchangeRateProvider(ABC):
    @abstractmethod
    async def get_rates(self, base_currency: str) -> Dict[str, Decimal]:
        raise NotImplementedError

    async def get_rate(self, base_currency: str, target_currency: str) -> Decimal:
        """
        Get rate for any pair.
        Strategy:
          1. Try direct rate (base → target)
          2. Try inverse rate (target → base, then invert)
          3. Try cross via USD (base → USD → target)
        """
        base = base_currency.upper()
        target = target_currency.upper()

        if base == target:
            return Decimal("1")

        # 1. Direct
        try:
            rates = await self.get_rates(base)
            if target in rates:
                return rates[target]
        except Exception:
            pass

        # 2. Inverse (get target→base, invert)
        try:
            rates = await self.get_rates(target)
            if base in rates and rates[base] != 0:
                return (Decimal("1") / rates[base]).quantize(Decimal("0.00000001"))
        except Exception:
            pass

        # 3. Cross via USD
        try:
            usd_rates = await self.get_rates("USD")
            base_to_usd = (Decimal("1") / usd_rates[base]) if base != "USD" else Decimal("1")
            usd_to_target = usd_rates.get(target)
            if base_to_usd and usd_to_target:
                return (base_to_usd * usd_to_target).quantize(Decimal("0.00000001"))
        except Exception:
            pass

        raise ExchangeRateUnavailableException(base, target)


class OpenExchangeAdapter(ExchangeRateProvider):
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


class FixerAdapter(ExchangeRateProvider):
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
                raise Exception(data.get("error", {}).get("info", "Fixer error"))
            return {k: Decimal(str(v)) for k, v in data.get("rates", {}).items()}
        except Exception as exc:
            logger.error("fixer_fetch_failed", error=str(exc))
            raise ExchangeRateUnavailableException(base_currency, "ALL") from exc


class MockExchangeAdapter(ExchangeRateProvider):
    """
    Complete mock rates for all supported currencies — all relative to USD.
    Cross-rates are computed automatically by the base class get_rate() method.
    """
    # All rates are USD-based (how many units of currency per 1 USD)
    USD_RATES: Dict[str, Decimal] = {
        "EUR": Decimal("0.92"),
        "GBP": Decimal("0.79"),
        "JPY": Decimal("157.50"),   # ← was missing, now included
        "CAD": Decimal("1.36"),
        "AUD": Decimal("1.53"),
        "CHF": Decimal("0.90"),
        "CNY": Decimal("7.25"),
        "INR": Decimal("83.50"),
        "NGN": Decimal("1520.00"),
        "GHS": Decimal("15.80"),
        "KES": Decimal("129.00"),
        "ZAR": Decimal("18.60"),
        "USD": Decimal("1.00"),
    }

    async def get_rates(self, base_currency: str) -> Dict[str, Decimal]:
        base = base_currency.upper()

        if base == "USD":
            return dict(self.USD_RATES)

        # Convert USD-based table to the requested base
        if base not in self.USD_RATES:
            raise ExchangeRateUnavailableException(base, "ALL")

        base_per_usd = self.USD_RATES[base]   # e.g. for EUR: 0.92
        result: Dict[str, Decimal] = {}

        for currency, usd_rate in self.USD_RATES.items():
            if currency == base:
                result[currency] = Decimal("1")
            else:
                # base→target = (USD→target) / (USD→base)
                result[currency] = (usd_rate / base_per_usd).quantize(Decimal("0.00000001"))

        return result


def get_exchange_rate_provider() -> ExchangeRateProvider:
    provider = settings.EXCHANGE_RATE_PROVIDER.lower()

    if provider == "open_exchange" and settings.OPEN_EXCHANGE_APP_ID:
        return OpenExchangeAdapter(app_id=settings.OPEN_EXCHANGE_APP_ID)

    if provider == "fixer" and settings.FIXER_API_KEY:
        return FixerAdapter(api_key=settings.FIXER_API_KEY)

    logger.info("using_mock_exchange_rate_provider")
    return MockExchangeAdapter()
