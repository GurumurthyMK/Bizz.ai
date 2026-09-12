"""Shared supervised trainer: balanced logistic regression, fixed split."""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

TEST_SIZE = 0.2
RANDOM_STATE = 42
MAX_ITER = 1000


class ClassificationMetrics(BaseModel):
    n_train: int
    n_test: int
    positive_rate: float
    precision: float
    recall: float
    f1: float
    roc_auc: float | None


def new_classifier() -> LogisticRegression:
    return LogisticRegression(max_iter=MAX_ITER, random_state=RANDOM_STATE, class_weight="balanced")


def split_dataset(
    matrix: np.ndarray, labels: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return train_test_split(
        matrix, labels, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=labels
    )


def evaluate_classifier(
    model: LogisticRegression,
    X_test: np.ndarray,
    y_test: np.ndarray,
    n_train: int,
) -> ClassificationMetrics:
    predicted = model.predict(X_test)
    try:
        proba = model.predict_proba(X_test)[:, 1]
    except (AttributeError, IndexError):
        proba = predicted.astype(float)
    roc_auc: float | None = None
    if len(set(y_test.tolist())) == 2:
        roc_auc = float(roc_auc_score(y_test, proba))
    return ClassificationMetrics(
        n_train=n_train,
        n_test=int(len(y_test)),
        positive_rate=float(np.mean(y_test)) if len(y_test) else 0.0,
        precision=float(precision_score(y_test, predicted, zero_division=0)),
        recall=float(recall_score(y_test, predicted, zero_division=0)),
        f1=float(f1_score(y_test, predicted, zero_division=0)),
        roc_auc=roc_auc,
    )


SIGNAL_PHRASES: dict[str, str] = {
    "recency_days": "no orders for {v:.0f} days",
    "first_order_days_ago": "customer for {v:.0f} days",
    "days_since_last_interaction": "no interaction for {v:.0f} days",
    "is_inactive_90d": "inactive for 90+ days",
    "order_trend_90d": "declining order trend",
    "revenue_trend_90d": "declining revenue trend",
    "interaction_trend_90d": "declining engagement trend",
    "refund_rate": "elevated refund rate ({v:.0%})",
    "support_interactions": "{v:.0f} support interactions",
    "completed_orders": "{v:.0f} completed orders",
    "total_revenue": "${v:,.0f} lifetime revenue",
    "avg_order_value": "${v:,.0f} average order value",
    "orders_last_90d": "{v:.0f} orders in the last 90 days",
    "orders_last_30d": "{v:.0f} orders in the last 30 days",
    "interactions_last_30d": "{v:.0f} interactions in the last 30 days",
    "purchase_interactions": "{v:.0f} purchase interactions",
    "browse_interactions": "{v:.0f} browsing interactions",
    "campaign_linked_interactions": "{v:.0f} campaign interactions",
    "is_recently_active": "active in the last 30 days",
    "has_orders": "has order history",
    "favorite_category_share": "concentrated category mix ({v:.0%})",
    "avg_discount_rate": "high discount usage ({v:.0%})",
    "active_span_days": "{v:.0f} days of purchase history",
    "distinct_products": "{v:.0f} distinct products purchased",
    "total_orders": "{v:.0f} total orders",
    "cancelled_orders": "{v:.0f} cancelled orders",
    "refunded_orders": "{v:.0f} refunded orders",
    "pending_orders": "{v:.0f} pending orders",
    "max_order_value": "${v:,.0f} largest order",
    "min_order_value": "${v:,.0f} smallest order",
    "total_quantity": "{v:.0f} items purchased",
    "distinct_categories": "{v:.0f} distinct categories",
    "distinct_brands": "{v:.0f} distinct brands",
    "refund_count": "{v:.0f} refunds",
    "refunded_amount": "${v:,.0f} refunded",
    "total_interactions": "{v:.0f} total interactions",
    "distinct_interaction_types": "{v:.0f} interaction types",
    "interactions_last_90d": "{v:.0f} interactions in 90 days",
    "orders_last_180d": "{v:.0f} orders in 180 days",
    "revenue_last_90d": "${v:,.0f} revenue in 90 days",
    "avg_days_between_orders": "{v:.0f}-day average order gap",
    "avg_quantity_per_order": "{v:.1f} items per order",
    "interaction_per_order": "{v:.1f} interactions per order",
    "purchase_conversion_rate": "{v:.0%} purchase conversion",
    "review_referral_interactions": "{v:.0f} reviews/referrals",
    "has_interactions": "has engagement history",
}


def describe_signal(name: str, raw_value: float) -> str:
    template = SIGNAL_PHRASES.get(name, f"{name}={{v:.2f}}")
    try:
        return template.format(v=raw_value)
    except (ValueError, KeyError):
        return f"{name}={raw_value:.2f}"


def top_signals(
    coefficients: np.ndarray,
    feature_names: list[str],
    standardized: np.ndarray,
    raw: np.ndarray,
    k: int = 3,
    empty_message: str = "no elevated signals",
) -> list[str]:
    """Top-k features pushing the prediction upward, as human phrases.

    Contribution = coefficient × standardized value; only positive
    contributions are reported, ordered deterministically (contribution
    descending, feature name as tiebreaker).
    """
    scored = sorted(
        (
            (float(coefficients[i]) * float(standardized[i]), feature_names[i], float(raw[i]))
            for i in range(len(feature_names))
        ),
        key=lambda item: (-item[0], item[1]),
    )
    signals = [describe_signal(name, value) for contrib, name, value in scored if contrib > 0][
        : max(0, k)
    ]
    return signals or [empty_message]
