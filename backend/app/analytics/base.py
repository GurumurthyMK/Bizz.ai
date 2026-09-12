"""Base analytics utilities: explicit reference dates, safe math, ranking.

Every analytical computation takes an explicit reference date so results are
reproducible and testable. ``None`` means "now (UTC)" and must only be used
at the outermost call boundary, never buried inside helpers.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def normalize_reference_date(value: datetime | date | None) -> datetime:
    """Return a timezone-aware UTC datetime for analytics boundaries."""
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def window_bounds(
    reference_date: datetime | date | None, history_days: int
) -> tuple[datetime, datetime]:
    """Inclusive (start, end) window ending at the reference date."""
    if history_days < 1:
        raise ValueError("history_days must be >= 1")
    end = normalize_reference_date(reference_date)
    start = end - timedelta(days=history_days)
    return start, end


def days_since(moment: datetime | None, reference: datetime) -> int | None:
    """Whole days from ``moment`` to ``reference``; None when no moment."""
    if moment is None:
        return None
    aware = ensure_aware(moment)
    ref = ensure_aware(reference)
    return max(0, (ref - aware).days)


def ensure_aware(moment: datetime) -> datetime:
    """Interpret naive datetimes (e.g. SQLite round-trips) as UTC."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns ``default`` instead of raising on zero denominator."""
    if denominator == 0:
        return default
    return numerator / denominator


def normalized_diff(recent: float, prior: float) -> float:
    """Trend in [-1, 1]: (recent - prior) / (recent + prior); 0 when both are 0."""
    total = recent + prior
    if total == 0:
        return 0.0
    return (recent - prior) / total


def percentile_rank(value: float, population: list[float]) -> float:
    """Fraction of ``population`` less than or equal to ``value``; 0.0 when empty."""
    if not population:
        return 0.0
    return sum(1 for item in population if item <= value) / len(population)


def quantile_breaks(values: list[float], parts: int) -> list[float]:
    """Deterministic (parts-1) cut points splitting sorted values into parts bins."""
    if parts < 2:
        raise ValueError("parts must be >= 2")
    if not values:
        return []
    ordered = sorted(values)
    n = len(ordered)
    breaks = []
    for part in range(1, parts):
        position = part * n / parts
        lower = ordered[max(0, min(n - 1, int(position)))]
        breaks.append(lower)
    # Deduplicate while preserving order (constant populations collapse bins).
    unique: list[float] = []
    for point in breaks:
        if not unique or point != unique[-1]:
            unique.append(point)
    return unique


def assign_bin(value: float, breaks: list[float]) -> int:
    """0-based bin index for ``value`` given ascending ``breaks``."""
    for index, point in enumerate(breaks):
        if value < point:
            return index
    return len(breaks)


def quintile_score(rank: int, population: int, invert: bool = False) -> int:
    """Deterministic 1–5 score from a 0-based rank within a population.

    Rank 0 is the "worst" (smallest frequency/monetary) unless ``invert``
    is set. Pass ``invert=True`` for ascending best-first orderings such as
    recency, where rank 0 (most recent) must score 5.
    """
    if population <= 0:
        raise ValueError("population must be >= 1")
    position = max(0, min(population - 1, rank))
    if invert:
        return 5 - (position * 5) // population
    return 1 + (position * 5) // population
