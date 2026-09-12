"""Data health: counts, missing values, integrity, freshness, last import.

Every figure is an aggregate over current tables — no sampling, no estimates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.import_job import ImportJob
from app.models.interaction import Interaction
from app.models.product import Product
from app.models.transaction import Transaction


def _count(db: Session, model: Any) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def get_data_health(db: Session) -> dict[str, Any]:
    counts = {
        "customers": _count(db, Customer),
        "products": _count(db, Product),
        "transactions": _count(db, Transaction),
        "campaigns": _count(db, Campaign),
        "interactions": _count(db, Interaction),
    }

    missing = {
        "customers_without_phone": db.scalar(
            select(func.count()).select_from(Customer).where(Customer.phone.is_(None))
        )
        or 0,
        "customers_without_city": db.scalar(
            select(func.count()).select_from(Customer).where(Customer.city.is_(None))
        )
        or 0,
        "products_without_brand": db.scalar(
            select(func.count()).select_from(Product).where(Product.brand.is_(None))
        )
        or 0,
    }

    orphan_transactions = (
        db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(
                ~select(1).where(Customer.id == Transaction.customer_id).exists()
                | ~select(1).where(Product.id == Transaction.product_id).exists()
            )
        )
        or 0
    )
    orphan_interactions = (
        db.scalar(
            select(func.count())
            .select_from(Interaction)
            .where(~select(1).where(Customer.id == Interaction.customer_id).exists())
        )
        or 0
    )
    over_discounted = (
        db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.discount > Transaction.quantity * Transaction.unit_price)
        )
        or 0
    )

    txn_min, txn_max = db.execute(
        select(func.min(Transaction.transaction_date), func.max(Transaction.transaction_date))
    ).one()
    last_interaction = db.scalar(select(func.max(Interaction.occurred_at)))

    last_job = db.scalars(select(ImportJob).order_by(ImportJob.id.desc()).limit(1)).first()

    return {
        "counts": counts,
        "missing_values": missing,
        "integrity": {
            "orphan_transactions": orphan_transactions,
            "orphan_interactions": orphan_interactions,
            "over_discounted_transactions": over_discounted,
        },
        "freshness": {
            "transaction_date_min": _iso(txn_min),
            "transaction_date_max": _iso(txn_max),
            "last_interaction_at": _iso(last_interaction),
        },
        "last_import": (
            {
                "entity": last_job.entity,
                "status": last_job.status,
                "filename": last_job.filename,
                "rows_total": last_job.rows_total,
                "rows_inserted": last_job.rows_inserted,
                "rows_failed": last_job.rows_failed,
                "created_at": _iso(last_job.created_at),
            }
            if last_job is not None
            else None
        ),
    }
