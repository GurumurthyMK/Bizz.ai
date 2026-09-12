"""Inference services: load persisted artifacts once, score without retraining.

Each ``predict_*`` function builds current features through the analytics
layer, validates them against the artifact's column contract, and returns
typed scores. Training code paths are never touched here.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.analytics.features import build_customer_features
from app.ml.churn import ChurnScore, load_churn
from app.ml.opportunity import OpportunityScore, score_customers
from app.ml.persistence import load_bundle
from app.ml.preprocessing import SEGMENT_FEATURES, vectors_from_records
from app.ml.purchase import PurchaseScore, load_purchase
from app.ml.segmentation import load_segmentation


def predict_segments(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    artifacts_dir: Path | None = None,
) -> list[dict]:
    """Customer id, cluster id, and business label from the persisted K-Means."""
    bundle = load_bundle("segmentation", artifacts_dir)
    model = load_segmentation(bundle)
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    if not records:
        return []
    matrix, ids = vectors_from_records(records, SEGMENT_FEATURES)
    summaries = {summary["cluster_id"]: summary for summary in bundle.get("summaries", [])}
    clusters = model.predict(matrix).tolist()
    return [
        {
            "customer_id": customer_id,
            "cluster_id": int(cluster_id),
            "business_label": summaries.get(int(cluster_id), {}).get("business_label", "Unknown"),
        }
        for customer_id, cluster_id in zip(ids, clusters, strict=True)
    ]


def predict_churn(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    artifacts_dir: Path | None = None,
) -> list[ChurnScore]:
    """Churn probabilities with supporting signals from the persisted model."""
    model = load_churn(load_bundle("churn", artifacts_dir))
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    if not records:
        return []
    return model.score_customers(records)


def predict_purchase(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    artifacts_dir: Path | None = None,
) -> list[PurchaseScore]:
    """Purchase probabilities with supporting signals from the persisted model."""
    model = load_purchase(load_bundle("purchase", artifacts_dir))
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    if not records:
        return []
    return model.score_customers(records)


def predict_opportunities(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    artifacts_dir: Path | None = None,
) -> list[OpportunityScore]:
    """Deterministic opportunity scores combining value, churn, and purchase signals."""
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    if not records:
        return []
    churn = {
        score.customer_id: score.churn_probability
        for score in predict_churn(db, reference_date, history_days, customer_ids, artifacts_dir)
    }
    purchase = {
        score.customer_id: score.purchase_probability
        for score in predict_purchase(db, reference_date, history_days, customer_ids, artifacts_dir)
    }
    return score_customers(records, churn, purchase)


__all__ = [
    "predict_churn",
    "predict_opportunities",
    "predict_purchase",
    "predict_segments",
]
