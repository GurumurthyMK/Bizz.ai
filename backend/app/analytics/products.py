"""Product analytics: sales, revenue, reach, refunds, and rollups."""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.analytics.base import (
    normalize_reference_date,
    safe_div,
    window_bounds,
)
from app.models.product import Product
from app.models.transaction import Transaction


class ProductMetrics(BaseModel):
    product_id: int
    sku: str
    name: str
    category: str
    brand: str | None
    units_sold: int
    revenue: float
    orders: int
    distinct_customers: int
    avg_quantity_per_order: float
    refund_count: int
    refunded_amount: float
    refund_rate: float
    last_sale_date: datetime | None
    recent_units_30d: int
    recent_revenue_30d: float


class CategorySummary(BaseModel):
    category: str
    products: int
    units_sold: int
    revenue: float
    orders: int
    distinct_customers: int


class BrandSummary(BaseModel):
    brand: str
    products: int
    units_sold: int
    revenue: float
    orders: int


def compute_product_metrics(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    product_ids: list[int] | None = None,
) -> list[ProductMetrics]:
    ref = normalize_reference_date(reference_date)
    start, end = window_bounds(ref, history_days)
    ref_30 = end - timedelta(days=30)

    if product_ids is None:
        product_ids = list(db.scalars(select(Product.id).order_by(Product.id)).all())
    id_filter = [Transaction.product_id.in_(product_ids)] if product_ids else []

    rows = db.execute(
        select(
            Transaction.product_id,
            func.sum(
                case((Transaction.status == "completed", Transaction.quantity), else_=0)
            ).label("units"),
            func.sum(
                case((Transaction.status == "completed", Transaction.total_amount), else_=0)
            ).label("revenue"),
            func.sum(case((Transaction.status == "completed", 1), else_=0)).label("orders"),
            func.count(func.distinct(Transaction.customer_id)).label("customers"),
            func.sum(case((Transaction.status == "refunded", 1), else_=0)).label("rf"),
            func.sum(
                case((Transaction.status == "refunded", Transaction.total_amount), else_=0)
            ).label("rfamt"),
            func.max(
                case((Transaction.status == "completed", Transaction.transaction_date), else_=None)
            ).label("last_sale"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_30),
                        Transaction.quantity,
                    ),
                    else_=0,
                )
            ).label("u30"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_30),
                        Transaction.total_amount,
                    ),
                    else_=0,
                )
            ).label("r30"),
            func.count().label("all_orders"),
        )
        .where(
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            *id_filter,
        )
        .group_by(Transaction.product_id)
    ).all()

    by_product = {int(row[0]): row for row in rows}
    details = (
        db.execute(select(Product).where(Product.id.in_(product_ids))).scalars().all()
        if product_ids
        else []
    )
    metrics = []
    for product in details:
        row = by_product.get(product.id)
        units = int(row[1] or 0) if row else 0
        revenue = float(row[2] or 0) if row else 0.0
        orders = int(row[3] or 0) if row else 0
        refunds = int(row[5] or 0) if row else 0
        all_orders = int(row[10] or 0) if row else 0
        metrics.append(
            ProductMetrics(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                category=product.category,
                brand=product.brand,
                units_sold=units,
                revenue=revenue,
                orders=orders,
                distinct_customers=int(row[4] or 0) if row else 0,
                avg_quantity_per_order=safe_div(float(units), float(orders)),
                refund_count=refunds,
                refunded_amount=float(row[6] or 0) if row else 0.0,
                refund_rate=safe_div(float(refunds), float(all_orders)),
                last_sale_date=row[7] if row else None,
                recent_units_30d=int(row[8] or 0) if row else 0,
                recent_revenue_30d=float(row[9] or 0) if row else 0.0,
            )
        )
    return metrics


def summarize_by_category(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
) -> list[CategorySummary]:
    ref = normalize_reference_date(reference_date)
    start, end = window_bounds(ref, history_days)
    completed_revenue = func.sum(
        case((Transaction.status == "completed", Transaction.total_amount), else_=0)
    )
    rows = db.execute(
        select(
            Product.category,
            func.count(func.distinct(Product.id)).label("products"),
            func.sum(
                case((Transaction.status == "completed", Transaction.quantity), else_=0)
            ).label("units"),
            completed_revenue.label("revenue"),
            func.sum(case((Transaction.status == "completed", 1), else_=0)).label("orders"),
            func.count(func.distinct(Transaction.customer_id)).label("customers"),
        )
        .outerjoin(
            Transaction,
            (Transaction.product_id == Product.id)
            & (Transaction.transaction_date >= start)
            & (Transaction.transaction_date <= end),
        )
        .group_by(Product.category)
        .order_by(completed_revenue.desc())
    ).all()
    return [
        CategorySummary(
            category=row[0],
            products=int(row[1]),
            units_sold=int(row[2] or 0),
            revenue=float(row[3] or 0),
            orders=int(row[4] or 0),
            distinct_customers=int(row[5] or 0),
        )
        for row in rows
    ]


def summarize_by_brand(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
) -> list[BrandSummary]:
    ref = normalize_reference_date(reference_date)
    start, end = window_bounds(ref, history_days)
    completed_revenue = func.sum(
        case((Transaction.status == "completed", Transaction.total_amount), else_=0)
    )
    rows = db.execute(
        select(
            Product.brand,
            func.count(func.distinct(Product.id)).label("products"),
            func.sum(
                case((Transaction.status == "completed", Transaction.quantity), else_=0)
            ).label("units"),
            completed_revenue.label("revenue"),
            func.sum(case((Transaction.status == "completed", 1), else_=0)).label("orders"),
        )
        .outerjoin(
            Transaction,
            (Transaction.product_id == Product.id)
            & (Transaction.transaction_date >= start)
            & (Transaction.transaction_date <= end),
        )
        .where(Product.brand.is_not(None))
        .group_by(Product.brand)
        .order_by(completed_revenue.desc())
    ).all()
    return [
        BrandSummary(
            brand=row[0],
            products=int(row[1]),
            units_sold=int(row[2] or 0),
            revenue=float(row[3] or 0),
            orders=int(row[4] or 0),
        )
        for row in rows
    ]


def top_products(
    metrics: list[ProductMetrics], by: str = "revenue", limit: int = 10
) -> list[ProductMetrics]:
    """Deterministic top-N with id tiebreaker. ``by`` is revenue, units, or orders."""
    key = {"revenue": "revenue", "units": "units_sold", "orders": "orders"}.get(by, "revenue")
    return sorted(metrics, key=lambda m: (-getattr(m, key), m.product_id))[: max(0, limit)]
