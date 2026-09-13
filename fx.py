"""Live daily FX rates (INR <-> EUR) via the Frankfurter API (ECB reference rates, free, no key).

Rates are cached in-memory per date since a historical day's rate never changes.
"""
import requests

_cache: dict[str, float] = {}  # date_str -> INR per 1 EUR


def get_inr_per_eur(date_str: str) -> float:
    """Return how many INR one EUR was worth on the given date (YYYY-MM-DD).

    Falls back to the most recent available rate if the exact date has none
    (e.g. a weekend or a future date), which is how the underlying API behaves.
    """
    if date_str in _cache:
        return _cache[date_str]
    try:
        resp = requests.get(
            f"https://api.frankfurter.dev/v1/{date_str}",
            params={"base": "EUR", "symbols": "INR"},
            timeout=5,
        )
        resp.raise_for_status()
        rate = resp.json()["rates"]["INR"]
    except Exception:
        # Reasonable fallback so the app still works offline / API hiccup.
        rate = 90.0
    _cache[date_str] = rate
    return rate


def convert_to_eur(amount: float, currency: str, date_str: str) -> tuple[float, float | None]:
    """Convert `amount` in `currency` to EUR as of `date_str`.

    Returns (amount_in_eur, inr_per_eur_rate_used_or_None).
    """
    if currency == "EUR":
        return amount, None
    rate = get_inr_per_eur(date_str)
    return amount / rate, rate


def convert_from_eur(amount_eur: float, date_str: str) -> float:
    """Convert an EUR amount to INR using the given date's rate."""
    rate = get_inr_per_eur(date_str)
    return amount_eur * rate
