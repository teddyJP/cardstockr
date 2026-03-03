"""
Convert amounts to USD using optional live API or fallback static rates.

Set EXCHANGE_RATE_API_URL (e.g. https://api.exchangerate-api.com/v4/latest/USD)
for periodic fetches; no API key needed for that provider. Otherwise uses
static fallback rates (approximate).
"""

from typing import Optional

import requests

from app.core.config import get_settings

# Fallback rates to USD (approximate; update periodically if not using API)
_FALLBACK_RATES_TO_USD = {
    "USD": 1.0,
    "CAD": 0.74,
    "GBP": 1.27,
    "EUR": 1.08,
    "JPY": 0.0067,
    "AUD": 0.65,
}


def _fetch_rates() -> dict:
    settings = get_settings()
    url = getattr(settings, "exchange_rate_api_url", None) or ""
    if not url or not url.startswith("http"):
        return {}
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if "rates" in data:
            return data["rates"]
    except Exception:
        pass
    return {}


def to_usd(amount: float, currency: str) -> float:
    """
    Convert amount in given currency to USD.
    Uses EXCHANGE_RATE_API_URL if set and valid, else fallback static rates.
    """
    if not currency or currency.upper() == "USD":
        return round(amount, 2)
    currency = currency.upper()
    rates = _fetch_rates()
    if rates:
        # API returns e.g. {"USD": 1, "EUR": 0.92} (base USD)
        rate = rates.get(currency)
        if rate is not None and rate > 0:
            return round(amount / rate, 2)
    rate = _FALLBACK_RATES_TO_USD.get(currency)
    if rate is not None:
        return round(amount * rate, 2)
    return round(amount, 2)
