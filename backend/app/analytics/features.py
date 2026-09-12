"""ML feature engineering: stable CustomerFeatures vectors from analytics.

``build_customer_features`` runs a fixed set of aggregate queries once and
assembles one record per customer — including customers with no orders or
no interactions (zeros and documented sentinels, never NaN). ``FEATURE_NAMES``
is the single source of truth for column order; ``to_matrix`` and
``to_dataset`` convert records for model training.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.analytics.base import ensure_aware, normalize_reference_date, safe_div
from app.analytics.customers import compute_customer_metrics

FEATURE_NAMES: list[str] = [
    # Purchase & frequency (12)
    "total_orders",
    "completed_orders",
    "cancelled_orders",
    "refunded_orders",
    "pending_orders",
    "recency_days",
    "first_order_days_ago",
    "active_span_days",
    "avg_days_between_orders",
    "orders_last_30d",
    "orders_last_90d",
    "orders_last_180d",
    # Revenue (8)
    "total_revenue",
    "avg_order_value",
    "max_order_value",
    "min_order_value",
    "total_discount",
    "avg_discount_rate",
    "revenue_last_90d",
    "revenue_trend_90d",
    # Basket (6)
    "total_quantity",
    "avg_quantity_per_order",
    "distinct_products",
    "distinct_categories",
    "distinct_brands",
    "favorite_category_share",
    # Refunds (3)
    "refund_count",
    "refund_rate",
    "refunded_amount",
    # Engagement (10)
    "total_interactions",
    "distinct_interaction_types",
    "interactions_last_30d",
    "interactions_last_90d",
    "days_since_last_interaction",
    "purchase_interactions",
    "browse_interactions",
    "support_interactions",
    "review_referral_interactions",
    "campaign_linked_interactions",
    # Trends & conversion (4)
    "order_trend_90d",
    "interaction_trend_90d",
    "purchase_conversion_rate",
    "interaction_per_order",
    # Indicators (4)
    "has_orders",
    "has_interactions",
    "is_recently_active",
    "is_inactive_90d",
]

# distinct_campaigns is computed for inspection but excluded from the ML
# vector (high-cardinality ids leak); campaign signal enters via linked counts.
assert len(FEATURE_NAMES) == 47, "FEATURE_NAMES changed; update tests and docs"


class CustomerFeatures(BaseModel):
    customer_id: int
    total_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    refunded_orders: int = 0
    pending_orders: int = 0
    recency_days: float = 0.0
    first_order_days_ago: float = 0.0
    active_span_days: float = 0.0
    avg_days_between_orders: float = 0.0
    orders_last_30d: int = 0
    orders_last_90d: int = 0
    orders_last_180d: int = 0
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    max_order_value: float = 0.0
    min_order_value: float = 0.0
    total_discount: float = 0.0
    avg_discount_rate: float = 0.0
    revenue_last_90d: float = 0.0
    revenue_trend_90d: float = 0.0
    total_quantity: int = 0
    avg_quantity_per_order: float = 0.0
    distinct_products: int = 0
    distinct_categories: int = 0
    distinct_brands: int = 0
    favorite_category_share: float = 0.0
    refund_count: int = 0
    refund_rate: float = 0.0
    refunded_amount: float = 0.0
    total_interactions: int = 0
    distinct_interaction_types: int = 0
    interactions_last_30d: int = 0
    interactions_last_90d: int = 0
    days_since_last_interaction: float = 0.0
    purchase_interactions: int = 0
    browse_interactions: int = 0
    support_interactions: int = 0
    review_referral_interactions: int = 0
    campaign_linked_interactions: int = 0
    order_trend_90d: float = 0.0
    interaction_trend_90d: float = 0.0
    purchase_conversion_rate: float = 0.0
    interaction_per_order: float = 0.0
    has_orders: float = 0.0
    has_interactions: float = 0.0
    is_recently_active: float = 0.0
    is_inactive_90d: float = 0.0

    def to_vector(self) -> list[float]:
        values = self.model_dump(exclude={"customer_id"})
        return [float(values[name]) for name in FEATURE_NAMES]


def build_customer_features(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
) -> list[CustomerFeatures]:
    """Batch feature generation for customers; deterministic for fixed inputs."""
    ref = normalize_reference_date(reference_date)
    metrics = compute_customer_metrics(db, ref, history_days, customer_ids)
    features: list[CustomerFeatures] = []
    for m in metrics:
        recency = float(m.recency_days) if m.recency_days is not None else float(history_days)
        first_ago = (
            (ensure_aware(ref) - ensure_aware(m.first_order_date)).days
            if m.first_order_date is not None
            else history_days
        )
        last_event_ago = (
            float(m.days_since_last_interaction)
            if m.days_since_last_interaction is not None
            else float(history_days)
        )
        recently_active = (m.recency_days is not None and m.recency_days <= 30) or (
            m.days_since_last_interaction is not None and m.days_since_last_interaction <= 30
        )
        features.append(
            CustomerFeatures(
                customer_id=m.customer_id,
                total_orders=m.total_orders,
                completed_orders=m.completed_orders,
                cancelled_orders=m.cancelled_orders,
                refunded_orders=m.refunded_orders,
                pending_orders=m.pending_orders,
                recency_days=recency,
                first_order_days_ago=float(first_ago),
                active_span_days=float(m.active_span_days),
                avg_days_between_orders=m.avg_days_between_orders,
                orders_last_30d=m.orders_last_30d,
                orders_last_90d=m.orders_last_90d,
                orders_last_180d=m.orders_last_180d,
                total_revenue=m.total_revenue,
                avg_order_value=m.avg_order_value,
                max_order_value=m.max_order_value,
                min_order_value=m.min_order_value,
                total_discount=m.total_discount,
                avg_discount_rate=safe_div(m.total_discount, m.total_revenue + m.total_discount),
                revenue_last_90d=m.revenue_last_90d,
                revenue_trend_90d=m.revenue_trend_90d,
                total_quantity=m.total_quantity,
                avg_quantity_per_order=safe_div(float(m.total_quantity), float(m.completed_orders)),
                distinct_products=m.distinct_products,
                distinct_categories=m.distinct_categories,
                distinct_brands=m.distinct_brands,
                favorite_category_share=m.favorite_category_share,
                refund_count=m.refund_count,
                refund_rate=m.refund_rate,
                refunded_amount=m.refunded_amount,
                total_interactions=m.total_interactions,
                distinct_interaction_types=m.distinct_interaction_types,
                interactions_last_30d=m.interactions_last_30d,
                interactions_last_90d=m.interactions_last_90d,
                days_since_last_interaction=last_event_ago,
                purchase_interactions=m.purchase_interactions,
                browse_interactions=m.browse_interactions,
                support_interactions=m.support_interactions,
                review_referral_interactions=m.review_referral_interactions,
                campaign_linked_interactions=m.campaign_linked_interactions,
                order_trend_90d=m.order_trend_90d,
                interaction_trend_90d=m.interaction_trend_90d,
                purchase_conversion_rate=safe_div(
                    float(m.purchase_interactions), float(m.total_interactions)
                ),
                interaction_per_order=safe_div(
                    float(m.total_interactions), float(m.completed_orders)
                ),
                has_orders=1.0 if m.completed_orders > 0 else 0.0,
                has_interactions=1.0 if m.total_interactions > 0 else 0.0,
                is_recently_active=1.0 if recently_active else 0.0,
                is_inactive_90d=1.0 if m.is_inactive_90d else 0.0,
            )
        )
    return features


def to_matrix(features: list[CustomerFeatures]) -> tuple[list[str], list[list[float]]]:
    """Feature names plus one row-vector per record, in FEATURE_NAMES order."""
    return list(FEATURE_NAMES), [record.to_vector() for record in features]


def to_dataset(features: list[CustomerFeatures]) -> list[dict[str, float | int]]:
    """Row-oriented dataset conversion (customer_id plus named features)."""
    rows: list[dict[str, float | int]] = []
    for record in features:
        row: dict[str, float | int] = {"customer_id": record.customer_id}
        row.update(dict(zip(FEATURE_NAMES, record.to_vector(), strict=False)))
        rows.append(row)
    return rows
