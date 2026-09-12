"""Intelligence materialization: persist real ML/analytics outputs.

A materialization run loads the persisted model artifacts, scores every
customer through the analytics feature layer, and *replaces* the
segments/predictions/opportunities tables plus customer segment assignments.
Replacement (not append) keeps the tables a faithful mirror of the latest
model output; reruns are idempotent.

Only customers scoring at or above ``OPPORTUNITY_MIN_SCORE`` get an
opportunity row. Estimated value is the customer's lifetime completed
revenue — the value exposed by the opportunity — and the recommended action
is a deterministic template per opportunity type.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from sqlalchemy import Table, bindparam, delete, func, select, update
from sqlalchemy.orm import Session

from app.analytics.base import normalize_reference_date
from app.analytics.features import build_customer_features
from app.ml.churn import load_churn
from app.ml.opportunity import score_customers
from app.ml.persistence import load_bundle
from app.ml.preprocessing import SEGMENT_FEATURES, vectors_from_records
from app.ml.purchase import load_purchase
from app.ml.segmentation import load_segmentation
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.models.segment import Segment

SEGMENT_MODEL_VERSION = "kmeans-v1"
CHURN_MODEL_VERSION = "logreg-v1"
PURCHASE_MODEL_VERSION = "logreg-v1"
OPPORTUNITY_MODEL_VERSION = "opp-engine-v1"

OPPORTUNITY_MIN_SCORE = 0.4

OPPORTUNITY_TYPE_BY_DRIVER: dict[str, str] = {
    "value": "high-value",
    "purchase": "purchase",
    "retention": "retention",
    "engagement": "engagement",
    "momentum": "growth",
}

RECOMMENDED_ACTIONS: dict[str, str] = {
    "high-value": "Prioritize for personal outreach and account review.",
    "purchase": "Send a personalized offer based on past purchases.",
    "retention": "Launch a targeted retention campaign before value is lost.",
    "engagement": "Re-engage with relevant content and campaign touchpoints.",
    "growth": "Nurture with cross-sell suggestions while momentum is positive.",
}


class MaterializationReport(BaseModel):
    reference_date: str
    history_days: int
    segments: int
    predictions: int
    opportunities: int
    customers_linked: int


class IntelligenceStatus(BaseModel):
    materialized: bool
    reference_date: str | None
    segments: int
    predictions: int
    opportunities: int
    customers_linked: int


def _opportunity_type(components: dict[str, float]) -> str:
    driver = max(components, key=lambda name: (components[name], name))
    return OPPORTUNITY_TYPE_BY_DRIVER[driver]


def materialize_intelligence(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    artifacts_dir: Path | None = None,
    opportunity_min_score: float = OPPORTUNITY_MIN_SCORE,
) -> MaterializationReport:
    """Score all customers and replace intelligence tables. Raises
    ModelNotTrainedError when artifacts are missing — never fakes output."""
    ref = normalize_reference_date(reference_date)

    seg_bundle = load_bundle("segmentation", artifacts_dir)
    segmentation = load_segmentation(seg_bundle)
    churn_model = load_churn(load_bundle("churn", artifacts_dir))
    purchase_model = load_purchase(load_bundle("purchase", artifacts_dir))

    records = build_customer_features(db, ref, history_days)
    by_customer = {record.customer_id: record for record in records}

    churn_scores = (
        {score.customer_id: score for score in churn_model.score_customers(records)}
        if records
        else {}
    )
    purchase_scores = (
        {score.customer_id: score for score in purchase_model.score_customers(records)}
        if records
        else {}
    )
    opportunities = score_customers(
        records,
        {cid: score.churn_probability for cid, score in churn_scores.items()},
        {cid: score.purchase_probability for cid, score in purchase_scores.items()},
    )

    # Replace children first, then segments; customer assignments are nulled
    # explicitly so the delete order never violates foreign keys.
    db.execute(delete(Opportunity))
    db.execute(delete(Prediction))
    db.execute(delete(Segment))
    db.execute(update(Customer).values(segment_id=None))

    segment_ids: dict[int, int] = {}
    if records:
        matrix, ids = vectors_from_records(records, SEGMENT_FEATURES)
        clusters = [int(label) for label in segmentation.predict(matrix).tolist()]
        summaries = {
            int(summary["cluster_id"]): summary for summary in seg_bundle.get("summaries", [])
        }
        run_silhouette = seg_bundle.get("silhouette")
        cluster_size = {cid: clusters.count(cid) for cid in set(clusters)}
        for cluster_id in sorted(cluster_size):
            summary = summaries.get(cluster_id, {})
            segment = Segment(
                cluster_id=cluster_id,
                name=str(summary.get("business_label", f"Cluster {cluster_id}")),
                size=cluster_size[cluster_id],
                share=cluster_size[cluster_id] / len(ids),
                avg_recency_days=float(summary.get("avg_recency_days", 0.0)),
                avg_completed_orders=float(summary.get("avg_completed_orders", 0.0)),
                avg_revenue=float(summary.get("avg_revenue", 0.0)),
                silhouette=run_silhouette,
                model_version=SEGMENT_MODEL_VERSION,
                reference_date=ref,
            )
            db.add(segment)
        db.flush()
        segment_ids = {
            int(row.cluster_id): int(row.id) for row in db.scalars(select(Segment)).all()
        }
        assignments = [
            {"b_id": customer_id, "b_seg": segment_ids[cluster_id]}
            for customer_id, cluster_id in zip(ids, clusters, strict=True)
        ]
        # Core executemany update (SET only segment_id, matched by PK). The
        # cast documents what SQLAlchemy guarantees at runtime: the mapped
        # table of an ORM class. ORM-enabled updates hijack executemany into
        # per-row PK mode, so Core is required here.
        customer_table = cast(Table, Customer.__table__)
        db.execute(
            customer_table.update()
            .where(customer_table.c.id == bindparam("b_id"))
            .values(segment_id=bindparam("b_seg")),
            assignments,
        )

    for customer_id, churn_score in churn_scores.items():
        db.add(
            Prediction(
                customer_id=customer_id,
                prediction_type="churn",
                probability=churn_score.churn_probability,
                band=churn_score.risk_band,
                signals=list(churn_score.signals),
                model_version=CHURN_MODEL_VERSION,
                reference_date=ref,
            )
        )
    for customer_id, purchase_score in purchase_scores.items():
        db.add(
            Prediction(
                customer_id=customer_id,
                prediction_type="purchase",
                probability=purchase_score.purchase_probability,
                band=purchase_score.likelihood_band,
                signals=list(purchase_score.signals),
                model_version=PURCHASE_MODEL_VERSION,
                reference_date=ref,
            )
        )

    # Column-only map: never hydrate full Customer rows (with their
    # transactions/interactions) just to read segment assignments.
    id_segment_rows = db.execute(select(Customer.id, Customer.segment_id)).all()
    customer_segment: dict[int, int | None] = {
        int(customer_id): segment_id for customer_id, segment_id in id_segment_rows
    }
    kept = 0
    for item in opportunities:
        if item.score < opportunity_min_score:
            continue
        opportunity_type = _opportunity_type(item.components)
        record = by_customer[item.customer_id]
        db.add(
            Opportunity(
                customer_id=item.customer_id,
                segment_id=customer_segment.get(item.customer_id),
                opportunity_type=opportunity_type,
                score=item.score,
                tier=item.tier,
                estimated_value=round(record.total_revenue, 2),
                reasons=list(item.reasons),
                signals=dict(item.components),
                recommended_action=RECOMMENDED_ACTIONS[opportunity_type],
                model_version=OPPORTUNITY_MODEL_VERSION,
                reference_date=ref,
            )
        )
        kept += 1

    db.commit()
    return MaterializationReport(
        reference_date=ref.isoformat(),
        history_days=history_days,
        segments=len(segment_ids),
        predictions=len(churn_scores) + len(purchase_scores),
        opportunities=kept,
        customers_linked=len(by_customer) if segment_ids else 0,
    )


def get_intelligence_status(db: Session) -> IntelligenceStatus:
    """Counts plus the latest materialization reference, if any."""
    segments = db.scalar(select(func.count()).select_from(Segment)) or 0
    predictions = db.scalar(select(func.count()).select_from(Prediction)) or 0
    opportunities = db.scalar(select(func.count()).select_from(Opportunity)) or 0
    linked = (
        db.scalar(
            select(func.count()).select_from(Customer).where(Customer.segment_id.is_not(None))
        )
        or 0
    )
    latest: datetime | None = db.scalar(select(func.max(Segment.reference_date)))
    return IntelligenceStatus(
        materialized=segments > 0,
        reference_date=latest.isoformat() if latest is not None else None,
        segments=segments,
        predictions=predictions,
        opportunities=opportunities,
        customers_linked=linked,
    )
