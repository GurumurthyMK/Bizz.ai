"""Customer analytics: purchase, revenue, engagement, and churn indicators.

All functions take an explicit reference date and history window; only rows
with event dates inside [reference - history_days, reference] contribute.
Customers without purchases or interactions yield zeros and documented
sentinels — never NaN, never dropped rows.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.analytics.base import (
    days_since,
    ensure_aware,
    normalize_reference_date,
    normalized_diff,
    safe_div,
    window_bounds,
)
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.product import Product
from app.models.transaction import Transaction


class CustomerMetrics(BaseModel):
    customer_id: int
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    refunded_orders: int
    pending_orders: int
    total_revenue: float
    total_quantity: int
    total_discount: float
    avg_order_value: float
    max_order_value: float
    min_order_value: float
    first_order_date: datetime | None
    last_order_date: datetime | None
    active_span_days: int
    avg_days_between_orders: float
    orders_last_30d: int
    orders_last_90d: int
    orders_last_180d: int
    revenue_last_90d: float
    revenue_prior_90d: float
    order_trend_90d: float
    revenue_trend_90d: float
    distinct_products: int
    distinct_categories: int
    distinct_brands: int
    favorite_category: str | None
    favorite_category_share: float
    refund_count: int
    refund_rate: float
    refunded_amount: float
    total_interactions: int
    distinct_interaction_types: int
    interactions_last_30d: int
    interactions_last_90d: int
    interactions_prior_90d: int
    interaction_trend_90d: float
    purchase_interactions: int
    browse_interactions: int
    support_interactions: int
    review_referral_interactions: int
    campaign_linked_interactions: int
    distinct_campaigns: int
    last_interaction_date: datetime | None
    days_since_last_interaction: int | None
    recency_days: int | None
    is_inactive_90d: bool


def compute_customer_metrics(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
) -> list[CustomerMetrics]:
    ref = normalize_reference_date(reference_date)
    start, end = window_bounds(ref, history_days)
    ref_30 = end - timedelta(days=30)
    ref_90 = end - timedelta(days=90)
    ref_180 = end - timedelta(days=180)

    if customer_ids is None:
        customer_ids = list(db.scalars(select(Customer.id).order_by(Customer.id)).all())
    txn_filter = [Transaction.customer_id.in_(customer_ids)] if customer_ids else []
    event_filter = [Interaction.customer_id.in_(customer_ids)] if customer_ids else []

    txn_rows = db.execute(
        select(
            Transaction.customer_id,
            func.count().label("total"),
            func.sum(case((Transaction.status == "completed", 1), else_=0)).label("done"),
            func.sum(case((Transaction.status == "cancelled", 1), else_=0)).label("cx"),
            func.sum(case((Transaction.status == "refunded", 1), else_=0)).label("rf"),
            func.sum(case((Transaction.status == "pending", 1), else_=0)).label("pd"),
            func.sum(
                case((Transaction.status == "completed", Transaction.total_amount), else_=0)
            ).label("revenue"),
            func.sum(
                case((Transaction.status == "completed", Transaction.quantity), else_=0)
            ).label("qty"),
            func.sum(
                case((Transaction.status == "completed", Transaction.discount), else_=0)
            ).label("disc"),
            func.max(
                case((Transaction.status == "completed", Transaction.total_amount), else_=None)
            ).label("mx"),
            func.min(
                case((Transaction.status == "completed", Transaction.total_amount), else_=None)
            ).label("mn"),
            func.min(
                case((Transaction.status == "completed", Transaction.transaction_date), else_=None)
            ).label("first"),
            func.max(
                case((Transaction.status == "completed", Transaction.transaction_date), else_=None)
            ).label("last"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_30),
                        1,
                    ),
                    else_=0,
                )
            ).label("o30"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_90),
                        1,
                    ),
                    else_=0,
                )
            ).label("o90"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_180),
                        1,
                    ),
                    else_=0,
                )
            ).label("o180"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_90),
                        Transaction.total_amount,
                    ),
                    else_=0,
                )
            ).label("r90"),
            func.sum(
                case(
                    (
                        (Transaction.status == "completed")
                        & (Transaction.transaction_date >= ref_180)
                        & (Transaction.transaction_date < ref_90),
                        Transaction.total_amount,
                    ),
                    else_=0,
                )
            ).label("rprior"),
            func.count(func.distinct(Transaction.product_id)).label("nprod"),
            func.sum(
                case((Transaction.status == "refunded", Transaction.total_amount), else_=0)
            ).label("rfamt"),
        )
        .where(
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            *txn_filter,
        )
        .group_by(Transaction.customer_id)
    ).all()

    cat_rows = db.execute(
        select(
            Transaction.customer_id,
            Product.category,
            func.sum(Transaction.total_amount).label("revenue"),
            func.count().label("orders"),
        )
        .join(Product, Product.id == Transaction.product_id)
        .where(
            Transaction.status == "completed",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            *txn_filter,
        )
        .group_by(Transaction.customer_id, Product.category)
    ).all()

    brand_rows = db.execute(
        select(
            Transaction.customer_id,
            func.count(func.distinct(Product.brand)).label("brands"),
        )
        .join(Product, Product.id == Transaction.product_id)
        .where(
            Transaction.status == "completed",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
            *txn_filter,
        )
        .group_by(Transaction.customer_id)
    ).all()

    event_rows = db.execute(
        select(
            Interaction.customer_id,
            func.count().label("total"),
            func.count(func.distinct(Interaction.interaction_type)).label("ntypes"),
            func.sum(case((Interaction.interaction_type == "purchase", 1), else_=0)).label("purch"),
            func.sum(
                case((Interaction.interaction_type.in_(["open", "click", "visit"]), 1), else_=0)
            ).label("browse"),
            func.sum(
                case((Interaction.interaction_type.in_(["support", "call"]), 1), else_=0)
            ).label("support"),
            func.sum(
                case((Interaction.interaction_type.in_(["review", "referral"]), 1), else_=0)
            ).label("revref"),
            func.sum(case((Interaction.campaign_id.is_not(None), 1), else_=0)).label("linked"),
            func.count(func.distinct(Interaction.campaign_id)).label("ncamp"),
            func.sum(case((Interaction.occurred_at >= ref_30, 1), else_=0)).label("e30"),
            func.sum(case((Interaction.occurred_at >= ref_90, 1), else_=0)).label("e90"),
            func.sum(
                case(
                    (
                        (Interaction.occurred_at >= ref_180) & (Interaction.occurred_at < ref_90),
                        1,
                    ),
                    else_=0,
                )
            ).label("eprior"),
            func.max(Interaction.occurred_at).label("last_event"),
        )
        .where(Interaction.occurred_at >= start, Interaction.occurred_at <= end, *event_filter)
        .group_by(Interaction.customer_id)
    ).all()

    from collections import defaultdict

    txn_by_customer = {row[0]: row for row in txn_rows}
    event_by_customer = {row[0]: row for row in event_rows}
    brands_by_customer = {row[0]: int(row[1]) for row in brand_rows}
    cats_by_customer: dict[int, list] = defaultdict(list)
    for customer_id, category, revenue, orders in cat_rows:
        cats_by_customer[int(customer_id)].append((category, float(revenue or 0), int(orders)))

    metrics: list[CustomerMetrics] = []
    for customer_id in customer_ids:
        t = txn_by_customer.get(customer_id)
        total = int(t[1]) if t else 0
        done = int(t[2]) if t else 0
        revenue = float(t[6] or 0) if t else 0.0
        qty = int(t[7] or 0) if t else 0
        disc = float(t[8] or 0) if t else 0.0
        first = t[11] if t else None
        last = t[12] if t else None
        o90 = int(t[14]) if t else 0
        o180 = int(t[15]) if t else 0
        r90 = float(t[16] or 0) if t else 0.0
        rprior = float(t[17] or 0) if t else 0.0
        rfamt = float(t[19] or 0) if t else 0.0

        span = (
            (ensure_aware(last) - ensure_aware(first)).days
            if first is not None and last is not None
            else 0
        )
        span = max(0, span)
        recency = days_since(last, ref)
        cats = cats_by_customer.get(customer_id, [])
        cat_revenue = sum(c[1] for c in cats)
        favorite = max(cats, key=lambda c: (c[1], c[0])) if cats else None

        e = event_by_customer.get(customer_id)
        events = int(e[1]) if e else 0
        e90 = int(e[10]) if e else 0
        eprior = int(e[11]) if e else 0
        last_event = e[12] if e else None

        metrics.append(
            CustomerMetrics(
                customer_id=customer_id,
                total_orders=total,
                completed_orders=done,
                cancelled_orders=int(t[3]) if t else 0,
                refunded_orders=int(t[4]) if t else 0,
                pending_orders=int(t[5]) if t else 0,
                total_revenue=revenue,
                total_quantity=qty,
                total_discount=disc,
                avg_order_value=safe_div(revenue, done),
                max_order_value=float(t[9]) if t and t[9] is not None else 0.0,
                min_order_value=float(t[10]) if t and t[10] is not None else 0.0,
                first_order_date=first,
                last_order_date=last,
                active_span_days=span,
                avg_days_between_orders=safe_div(float(span), float(done - 1)) if done > 1 else 0.0,
                orders_last_30d=int(t[13]) if t else 0,
                orders_last_90d=o90,
                orders_last_180d=o180,
                revenue_last_90d=r90,
                revenue_prior_90d=rprior,
                order_trend_90d=normalized_diff(float(o90), float(o180 - o90)),
                revenue_trend_90d=normalized_diff(r90, rprior),
                distinct_products=int(t[18]) if t else 0,
                distinct_categories=len(cats),
                distinct_brands=brands_by_customer.get(customer_id, 0),
                favorite_category=favorite[0] if favorite else None,
                favorite_category_share=safe_div(favorite[1], cat_revenue) if favorite else 0.0,
                refund_count=int(t[4]) if t else 0,
                refund_rate=safe_div(float(int(t[4]) if t else 0), float(total)),
                refunded_amount=rfamt,
                total_interactions=events,
                distinct_interaction_types=int(e[2]) if e else 0,
                interactions_last_30d=int(e[9]) if e else 0,
                interactions_last_90d=e90,
                interactions_prior_90d=eprior,
                interaction_trend_90d=normalized_diff(float(e90), float(eprior)),
                purchase_interactions=int(e[3]) if e else 0,
                browse_interactions=int(e[4]) if e else 0,
                support_interactions=int(e[5]) if e else 0,
                review_referral_interactions=int(e[6]) if e else 0,
                campaign_linked_interactions=int(e[7]) if e else 0,
                distinct_campaigns=max(0, int(e[8]) if e else 0),
                last_interaction_date=last_event,
                days_since_last_interaction=days_since(last_event, ref),
                recency_days=recency,
                is_inactive_90d=(recency is None) or recency > 90,
            )
        )
    return metrics


def get_customer_metrics(
    db: Session,
    customer_id: int,
    reference_date: datetime | None = None,
    history_days: int = 365,
) -> CustomerMetrics:
    """Single-customer convenience wrapper around the batch computation."""
    return compute_customer_metrics(db, reference_date, history_days, [customer_id])[0]
