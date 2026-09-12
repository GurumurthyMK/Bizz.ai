"""RFM analytics: recency, frequency, monetary scoring and segment labels.

Inputs come from completed transactions inside an explicit history window.
Quintile scores are rank-based with ``customer_id`` as the tiebreaker, so
identical data always yields identical scores. Customers with no completed
orders receive R=F=M=1 (Lost / Low Value) instead of being dropped.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.base import (
    days_since,
    normalize_reference_date,
    quintile_score,
    window_bounds,
)
from app.models.customer import Customer
from app.models.transaction import Transaction


class RFMRecord(BaseModel):
    customer_id: int
    recency_days: int | None
    frequency: int
    monetary: float
    r_score: int
    f_score: int
    m_score: int
    rfm_code: str
    segment: str
    value_tier: str


def classify_segment(r_score: int, f_score: int) -> str:
    """Deterministic RFM segment; rules are ordered and fully partition 1–5."""
    if r_score == 5 and f_score == 1:
        return "New"
    if r_score >= 4 and f_score >= 4:
        return "Champions"
    if r_score >= 3 and f_score >= 3:
        return "Loyal"
    if r_score >= 4:
        return "Potential Loyalists"
    if r_score <= 2 and f_score >= 4:
        return "Cannot Lose Them"
    if r_score == 3:
        return "Emerging"
    if r_score == 2:
        return "At Risk"
    return "Lost"


def classify_value_tier(m_score: int) -> str:
    if m_score >= 4:
        return "High Value"
    if m_score == 3:
        return "Medium Value"
    return "Low Value"


def _score_sorted(ordered_ids: list[int], invert: bool) -> dict[int, int]:
    """Assign 1–5 scores to pre-sorted ids (rank 0 scores 1, or 5 if inverted)."""
    population = len(ordered_ids)
    return {
        customer_id: quintile_score(rank, population, invert=invert)
        for rank, customer_id in enumerate(ordered_ids)
    }


def compute_rfm(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
) -> list[RFMRecord]:
    """RFM records for customers with completed orders in the window.

    Customers without completed orders (or entirely unknown ids) are included
    with R=F=M=1 so downstream stages never silently drop rows.
    """
    ref = normalize_reference_date(reference_date)
    start, end = window_bounds(ref, history_days)

    if customer_ids is None:
        customer_ids = list(db.scalars(select(Customer.id).order_by(Customer.id)).all())

    rows = db.execute(
        select(
            Transaction.customer_id,
            func.count().label("orders"),
            func.sum(Transaction.total_amount).label("revenue"),
            func.max(Transaction.transaction_date).label("last_order"),
        )
        .where(
            Transaction.status == "completed",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            *([Transaction.customer_id.in_(customer_ids)] if customer_ids else []),
        )
        .group_by(Transaction.customer_id)
    ).all()

    by_customer: dict[int, tuple[int, float, datetime | None]] = {}
    for customer_id, orders, revenue, last_order in rows:
        by_customer[int(customer_id)] = (
            int(orders),
            float(revenue or Decimal("0")),
            last_order,
        )

    recency: dict[int, int | None] = {}
    for customer_id in customer_ids:
        entry = by_customer.get(customer_id)
        recency[customer_id] = days_since(entry[2], ref) if entry is not None else None

    # Best-first orderings; customer_id tiebreaker keeps scores deterministic.
    # Recency sorts ascending (most recent first, rank 0 = best → inverted to 5).
    # Frequency/monetary sort ascending (smallest first, rank 0 = worst → 1).
    recency_order = sorted(
        customer_ids, key=lambda cid: (recency[cid] is None, recency[cid] or 0, cid)
    )
    frequency_order = sorted(
        customer_ids,
        key=lambda cid: (by_customer.get(cid, (0, 0.0, None))[0], cid),
    )
    monetary_order = sorted(
        customer_ids,
        key=lambda cid: (by_customer.get(cid, (0, 0.0, None))[1], cid),
    )
    r_scores = _score_sorted(recency_order, invert=True)
    f_scores = _score_sorted(frequency_order, invert=False)
    m_scores = _score_sorted(monetary_order, invert=False)

    records = []
    for customer_id in customer_ids:
        orders, revenue, _ = by_customer.get(customer_id, (0, 0.0, None))
        r_score, f_score, m_score = (
            r_scores[customer_id],
            f_scores[customer_id],
            m_scores[customer_id],
        )
        records.append(
            RFMRecord(
                customer_id=customer_id,
                recency_days=recency[customer_id],
                frequency=orders,
                monetary=revenue,
                r_score=r_score,
                f_score=f_score,
                m_score=m_score,
                rfm_code=f"{r_score}{f_score}{m_score}",
                segment=classify_segment(r_score, f_score),
                value_tier=classify_value_tier(m_score),
            )
        )
    return records
