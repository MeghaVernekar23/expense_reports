"""Pure formatting/date/aggregation helpers shared across pages — no UI code."""
from datetime import date, datetime

from theme import CRITICAL, CURRENCY_SYMBOLS, GOOD, WARN

import storage


def fmt_money(v: float, currency: str = "EUR") -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, "")
    return f"{symbol}{v:,.2f}"


def fmt_eur(v: float) -> str:
    return fmt_money(v, "EUR")


def parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_remaining(end_str: str | None) -> int | None:
    end = parse_date(end_str)
    if end is None:
        return None
    delta = (end - date.today()).days
    return max(delta, 0)


def is_active_period(cat) -> bool:
    """A category shows on the dashboard only while manually switched on.
    This is independent of its period dates — those stay purely
    informational (labels, days-remaining, per-day-rate math)."""
    return cat.is_active


def status_color(pct_used: float) -> str:
    if pct_used >= 100:
        return CRITICAL
    if pct_used >= 75:
        return WARN
    return GOOD


def pace_status(cat, spent: float) -> tuple[str, str]:
    """Compare spend pace against the elapsed share of the category's period,
    so overspending shows red/yellow even while % of budget still looks fine.

    Returns (color, short_label). Falls back to plain % thresholds when the
    category has no dated period to pace against.
    """
    budget = cat.budget or 0
    pct_used = (spent / budget * 100) if budget > 0 else 0

    start = parse_date(cat.period_start)
    end = parse_date(cat.period_end)
    if not (start and end) or budget <= 0:
        if pct_used >= 100:
            return CRITICAL, "Over budget"
        if pct_used >= 75:
            return WARN, "Watch spending"
        return GOOD, "On track"

    total_days = max((end - start).days, 1)
    elapsed_days = min(max((date.today() - start).days, 0), total_days)
    pct_elapsed = elapsed_days / total_days * 100

    # how far ahead of the "fair" pace this category's spend is
    drift = pct_used - pct_elapsed

    if pct_used >= 100 or drift >= 20:
        return CRITICAL, "Spending too fast"
    if drift >= 8:
        return WARN, "Ahead of pace"
    return GOOD, "On track"


def monthly_totals(expenses) -> list[tuple[str, float]]:
    """Bucket expenses by calendar month (YYYY-MM), summed in EUR, sorted
    chronologically. Calendar months are used here rather than each
    category's own custom period, so spend lines up the same way no
    matter how a category's billing cycle is dated (e.g. 14th-to-14th)."""
    buckets: dict[str, float] = {}
    for e in expenses:
        d = parse_date(e.spent_on)
        if d is None:
            continue
        key = d.strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0) + e.amount_eur
    return sorted(buckets.items())


def yearly_totals(expenses) -> list[tuple[str, float]]:
    buckets: dict[str, float] = {}
    for e in expenses:
        d = parse_date(e.spent_on)
        if d is None:
            continue
        key = d.strftime("%Y")
        buckets[key] = buckets.get(key, 0) + e.amount_eur
    return sorted(buckets.items())


def monthly_daily_totals(expenses) -> list[tuple[date, float]]:
    """Bucket a set of expenses by exact day, summed in EUR, sorted
    chronologically — the line the dashboard's 'spend over time' chart
    plots for whatever period the given expenses belong to."""
    buckets: dict[date, float] = {}
    for e in expenses:
        d = parse_date(e.spent_on)
        if d is None:
            continue
        buckets[d] = buckets.get(d, 0) + e.amount_eur
    return sorted(buckets.items())


def category_groups() -> dict[str, list]:
    """All categories grouped by name, each group's periods sorted
    chronologically — the basis for month-over-month analysis of a
    recurring category like 'General'."""
    groups: dict[str, list] = {}
    for c in storage.get_categories():
        groups.setdefault(c.name, []).append(c)
    for group in groups.values():
        group.sort(key=lambda c: c.period_start or "")
    return groups
