"""Database insertion, idempotency guard, reset, and audit for the demo dataset.

Generation lives in ``app.seed.generator``; this module only moves rows.
Keys starting with ``_`` in generated dicts are generation helpers and are
stripped before insert.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, insert, or_, select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.product import Product
from app.models.transaction import Transaction
from app.seed.generator import GeneratedDataset, SeedConfig, generate

BATCH_SIZE = 5000


class SeedError(Exception):
    """Raised when seeding would silently duplicate or destroy data."""


def _clean(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]


def table_counts(db: Session) -> dict[str, int]:
    return {
        "customers": db.scalar(select(func.count()).select_from(Customer)) or 0,
        "products": db.scalar(select(func.count()).select_from(Product)) or 0,
        "transactions": db.scalar(select(func.count()).select_from(Transaction)) or 0,
        "campaigns": db.scalar(select(func.count()).select_from(Campaign)) or 0,
        "interactions": db.scalar(select(func.count()).select_from(Interaction)) or 0,
    }


def _insert_batches(db: Session, table: Any, rows: list[dict[str, Any]]) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        db.execute(insert(table), _clean(rows[start : start + BATCH_SIZE]))


def _ordered_ids(db: Session, model: Any) -> list[int]:
    return list(db.scalars(select(model.id).order_by(model.id)).all())


def reset_dataset(db: Session) -> dict[str, int]:
    """Delete all business rows (children first). Never touches users/auth data."""
    before = table_counts(db)
    db.execute(delete(Interaction))
    db.execute(delete(Transaction))
    db.execute(delete(Campaign))
    db.execute(delete(Customer))
    db.execute(delete(Product))
    db.commit()
    return before


def seed_dataset(
    db: Session,
    config: SeedConfig | None = None,
    *,
    reset: bool = False,
) -> dict[str, Any]:
    """Generate and insert the demo dataset. Returns counts plus audit info.

    Refuses to run when business tables already hold rows unless
    ``reset=True`` is passed explicitly — seeding must never silently
    duplicate business data.
    """
    config = config or SeedConfig()
    existing = table_counts(db)
    if any(existing.values()):
        if not reset:
            raise SeedError(
                "Business tables already contain data "
                f"({', '.join(f'{k}={v}' for k, v in existing.items() if v)}). "
                "Re-run with reset=True to replace the dataset explicitly."
            )
        reset_dataset(db)

    data: GeneratedDataset = generate(config)

    _insert_batches(db, Product, data.products)
    _insert_batches(db, Campaign, data.campaigns)
    _insert_batches(db, Customer, data.customers)
    customer_ids = _ordered_ids(db, Customer)
    product_ids = _ordered_ids(db, Product)
    campaign_ids = _ordered_ids(db, Campaign)

    for txn in data.transactions:
        txn["customer_id"] = customer_ids[txn.pop("customer_idx")]
        txn["product_id"] = product_ids[txn.pop("product_idx")]
    _insert_batches(db, Transaction, data.transactions)

    for event in data.interactions:
        event["customer_id"] = customer_ids[event.pop("customer_idx")]
        campaign_idx = event.pop("campaign_idx")
        event["campaign_id"] = campaign_ids[campaign_idx] if campaign_idx is not None else None
    _insert_batches(db, Interaction, data.interactions)

    db.commit()
    report: dict[str, Any] = {
        "seed": config.seed,
        "customers": config.customers,
        "anchor": config.anchor.isoformat(),
        "counts": table_counts(db),
    }
    report["audit"] = audit_dataset(db)
    return report


def audit_dataset(db: Session) -> dict[str, Any]:
    """Validation snapshot: counts, date spans, integrity, value distributions."""
    orphan_txns = (
        db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(
                or_(
                    ~select(1).where(Customer.id == Transaction.customer_id).exists(),
                    ~select(1).where(Product.id == Transaction.product_id).exists(),
                )
            )
        )
        or 0
    )
    orphan_events = (
        db.scalar(
            select(func.count())
            .select_from(Interaction)
            .where(
                or_(
                    ~select(1).where(Customer.id == Interaction.customer_id).exists(),
                    and_(
                        Interaction.campaign_id.is_not(None),
                        ~select(1).where(Campaign.id == Interaction.campaign_id).exists(),
                    ),
                )
            )
        )
        or 0
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Transaction.total_amount), 0)).where(
            Transaction.status == "completed"
        )
    )
    txn_dates = db.execute(
        select(func.min(Transaction.transaction_date), func.max(Transaction.transaction_date))
    ).one()
    event_dates = db.execute(
        select(func.min(Interaction.occurred_at), func.max(Interaction.occurred_at))
    ).one()
    customers_with_orders = (
        db.scalar(select(func.count(func.distinct(Transaction.customer_id)))) or 0
    )
    status_mix = {
        row[0]: row[1]
        for row in db.execute(
            select(Transaction.status, func.count()).group_by(Transaction.status)
        ).all()
    }
    top_categories = [
        {"category": row[0], "transactions": row[1]}
        for row in db.execute(
            select(Product.category, func.count())
            .join(Transaction, Transaction.product_id == Product.id)
            .group_by(Product.category)
            .order_by(func.count().desc())
        ).all()
    ]

    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    return {
        "orphan_transactions": orphan_txns,
        "orphan_interactions": orphan_events,
        "completed_revenue": float(revenue or 0),
        "transaction_date_min": _iso(txn_dates[0]),
        "transaction_date_max": _iso(txn_dates[1]),
        "interaction_date_min": _iso(event_dates[0]),
        "interaction_date_max": _iso(event_dates[1]),
        "customers_with_orders": customers_with_orders,
        "transaction_status_mix": status_mix,
        "transactions_by_category": top_categories,
    }
