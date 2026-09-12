"""Supervised label definitions with explicit temporal semantics.

Models are trained on features computed *as of* a historical reference date,
with labels observed in a later outcome window. This mirrors production use
(features as of today, outcomes in the future) and prevents label leakage:

- churn:    features @ T, label = 1 if the customer had >= 1 completed order
            on/before T but zero completed orders in (T, T + 90 days].
- purchase: features @ T, label = 1 if >= 1 completed order in (T, T + 30 days].

Customers with no completed order on/before T are ineligible for churn
training (there is nothing to churn from) and are omitted from its labels.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.base import normalize_reference_date
from app.models.transaction import Transaction

CHURN_HORIZON_DAYS = 90
PURCHASE_HORIZON_DAYS = 30


def churn_labels(
    db: Session,
    reference_date: datetime | None = None,
    horizon_days: int = CHURN_HORIZON_DAYS,
    customer_ids: list[int] | None = None,
) -> dict[int, int]:
    """Customer id -> churn label. Only previously-active customers are eligible."""
    ref = normalize_reference_date(reference_date)
    horizon_end = ref + timedelta(days=horizon_days)
    scope = [Transaction.customer_id.in_(customer_ids)] if customer_ids else []

    prior = {
        int(row[0])
        for row in db.execute(
            select(Transaction.customer_id)
            .where(
                Transaction.status == "completed",
                Transaction.transaction_date <= ref,
                *scope,
            )
            .distinct()
        ).all()
    }
    if not prior:
        return {}
    retained = {
        int(row[0])
        for row in db.execute(
            select(Transaction.customer_id)
            .where(
                Transaction.status == "completed",
                Transaction.transaction_date > ref,
                Transaction.transaction_date <= horizon_end,
                Transaction.customer_id.in_(list(prior)),
            )
            .distinct()
        ).all()
    }
    return {customer_id: int(customer_id not in retained) for customer_id in prior}


def purchase_labels(
    db: Session,
    reference_date: datetime | None = None,
    horizon_days: int = PURCHASE_HORIZON_DAYS,
    customer_ids: list[int] | None = None,
) -> dict[int, int]:
    """Customer id -> bought-in-window label. Every in-scope customer is eligible."""
    ref = normalize_reference_date(reference_date)
    horizon_end = ref + timedelta(days=horizon_days)

    if customer_ids is None:
        from app.models.customer import Customer

        customer_ids = list(db.scalars(select(Customer.id).order_by(Customer.id)).all())
    scope = [Transaction.customer_id.in_(customer_ids)] if customer_ids else []
    buyers = {
        int(row[0])
        for row in db.execute(
            select(Transaction.customer_id)
            .where(
                Transaction.status == "completed",
                Transaction.transaction_date > ref,
                Transaction.transaction_date <= horizon_end,
                *scope,
            )
            .distinct()
        ).all()
    }
    return {customer_id: int(customer_id in buyers) for customer_id in customer_ids}


def label_rate(labels: dict[int, int]) -> float:
    if not labels:
        return 0.0
    return sum(labels.values()) / len(labels)
