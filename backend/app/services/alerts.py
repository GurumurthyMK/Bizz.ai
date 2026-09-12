"""Deterministic alert detection over persisted intelligence and aggregates.

Conditions (thresholds are module constants, documented here):
- high churn risk: persisted churn probability >= 0.66, top 20 by lifetime
  revenue (individual, customer-linked).
- revenue anomaly: trailing-30d completed revenue down >= 15% (high) or up
  >= 30% (medium) vs the prior 30 days.
- engagement decline: trailing-30d interactions down >= 20% (medium).
- new opportunity: persisted high-tier opportunities, top 10 by score
  (individual, opportunity- and customer-linked).
- segment change: segment with >= 50 members where >= 40% are high churn
  risk (high, segment-linked).

Every candidate carries a dedup_key bound to the reference month, so
re-running detection never duplicates. ML-dependent conditions read the
materialized predictions/opportunities tables — no model inference here —
and simply yield nothing when those tables are empty.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.base import normalize_reference_date
from app.models.alert import Alert
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.models.segment import Segment
from app.models.transaction import Transaction
from app.schemas.common import MAX_PAGE_SIZE
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate

CHURN_THRESHOLD = 0.66
CHURN_TOP_N = 20
REVENUE_DROP_PCT = 15.0
REVENUE_SPIKE_PCT = 30.0
ENGAGEMENT_DROP_PCT = 20.0
OPPORTUNITY_TOP_N = 10
SEGMENT_MIN_SIZE = 50
SEGMENT_RISK_SHARE = 0.40
WINDOW_DAYS = 30


def _period_label(ref: datetime) -> str:
    return ref.date().isoformat()[:7]


def _window_sums(db: Session, start: datetime, end: datetime) -> tuple[float, int, int]:
    """Completed revenue, completed orders, interaction count in a window."""
    revenue, orders = db.execute(
        select(
            func.coalesce(func.sum(Transaction.total_amount), 0),
            func.count(),
        ).where(
            Transaction.status == "completed",
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
    ).one()
    interactions = (
        db.scalar(
            select(func.count())
            .select_from(Interaction)
            .where(Interaction.occurred_at >= start, Interaction.occurred_at <= end)
        )
        or 0
    )
    return float(revenue or 0), int(orders or 0), interactions


def _detect_churn_candidates(db: Session, period: str) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Prediction.customer_id, Prediction.probability)
        .where(
            Prediction.prediction_type == "churn",
            Prediction.probability >= CHURN_THRESHOLD,
        )
        .order_by(Prediction.probability.desc())
    ).all()
    if not rows:
        return []
    # One grouped query for all candidates' lifetime revenue (no per-row queries).
    revenue_rows = db.execute(
        select(
            Transaction.customer_id,
            func.coalesce(func.sum(Transaction.total_amount), 0),
        )
        .where(
            Transaction.customer_id.in_([int(customer_id) for customer_id, _ in rows]),
            Transaction.status == "completed",
        )
        .group_by(Transaction.customer_id)
    ).all()
    revenues: dict[int, float] = {
        int(customer_id): float(total) for customer_id, total in revenue_rows
    }
    candidates = [
        {
            "customer_id": int(customer_id),
            "probability": float(probability),
            "revenue": float(revenues.get(int(customer_id), 0)),
        }
        for customer_id, probability in rows
    ]
    candidates.sort(key=lambda item: (-item["revenue"], item["customer_id"]))
    alerts = []
    for item in candidates[:CHURN_TOP_N]:
        alerts.append(
            {
                "alert_type": "high_churn_risk",
                "severity": "high",
                "title": f"High churn risk: customer {item['customer_id']}",
                "description": (
                    f"Churn probability {item['probability']:.0%} with "
                    f"${item['revenue']:,.0f} lifetime revenue exposed."
                ),
                "evidence": {
                    "customer_id": item["customer_id"],
                    "churn_probability": round(item["probability"], 4),
                    "lifetime_revenue": round(item["revenue"], 2),
                },
                "entity_type": "customer",
                "entity_id": item["customer_id"],
                "dedup_key": f"churn:{item['customer_id']}:{period}",
            }
        )
    return alerts


def _detect_revenue_anomaly(db: Session, ref: datetime, period: str) -> list[dict[str, Any]]:
    cur_start = ref - timedelta(days=WINDOW_DAYS)
    prev_start = ref - timedelta(days=2 * WINDOW_DAYS)
    current, _, _ = _window_sums(db, cur_start, ref)
    previous, _, _ = _window_sums(db, prev_start, cur_start)
    if previous == 0:
        return []
    change = (current - previous) / previous * 100
    if change <= -REVENUE_DROP_PCT:
        severity, direction = "high", "down"
    elif change >= REVENUE_SPIKE_PCT:
        severity, direction = "medium", "up"
    else:
        return []
    return [
        {
            "alert_type": "revenue_anomaly",
            "severity": severity,
            "title": f"Revenue {direction} {abs(change):.1f}% in 30 days",
            "description": (
                f"Completed revenue moved from ${previous:,.0f} to ${current:,.0f} "
                f"({change:+.1f}%) vs the prior 30 days."
            ),
            "evidence": {
                "current_revenue": round(current, 2),
                "previous_revenue": round(previous, 2),
                "change_pct": round(change, 1),
            },
            "entity_type": "metric",
            "entity_id": None,
            "dedup_key": f"revenue:{period}:{direction}",
        }
    ]


def _detect_engagement_decline(db: Session, ref: datetime, period: str) -> list[dict[str, Any]]:
    cur_start = ref - timedelta(days=WINDOW_DAYS)
    prev_start = ref - timedelta(days=2 * WINDOW_DAYS)
    _, _, current = _window_sums(db, cur_start, ref)
    _, _, previous = _window_sums(db, prev_start, cur_start)
    if previous == 0:
        return []
    change = (current - previous) / previous * 100
    if change > -ENGAGEMENT_DROP_PCT:
        return []
    return [
        {
            "alert_type": "engagement_decline",
            "severity": "medium",
            "title": f"Engagement down {abs(change):.1f}% in 30 days",
            "description": (
                f"Logged interactions fell from {previous:,} to {current:,} "
                f"({change:+.1f}%) vs the prior 30 days."
            ),
            "evidence": {
                "current_interactions": current,
                "previous_interactions": previous,
                "change_pct": round(change, 1),
            },
            "entity_type": "metric",
            "entity_id": None,
            "dedup_key": f"engagement:{period}",
        }
    ]


def _detect_new_opportunities(db: Session, period: str) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(Opportunity)
            .where(Opportunity.tier == "high")
            .order_by(Opportunity.score.desc())
            .limit(OPPORTUNITY_TOP_N)
        )
        .scalars()
        .all()
    )
    alerts = []
    for opportunity in rows:
        alerts.append(
            {
                "alert_type": "new_opportunity",
                "severity": "medium",
                "title": (
                    f"High-value opportunity: {opportunity.opportunity_type} "
                    f"(customer {opportunity.customer_id})"
                ),
                "description": (
                    f"Opportunity score {opportunity.score:.0%} with estimated value "
                    f"${float(opportunity.estimated_value):,.0f}. {opportunity.recommended_action}"
                ),
                "evidence": {
                    "opportunity_id": opportunity.id,
                    "customer_id": opportunity.customer_id,
                    "score": round(opportunity.score, 4),
                    "estimated_value": float(opportunity.estimated_value),
                },
                "entity_type": "opportunity",
                "entity_id": opportunity.id,
                "dedup_key": f"opportunity:{opportunity.id}:{period}",
            }
        )
    return alerts


def _detect_segment_change(db: Session, period: str) -> list[dict[str, Any]]:
    segments = db.scalars(select(Segment)).all()
    alerts = []
    for segment in segments:
        members = (
            db.scalar(
                select(func.count()).select_from(Customer).where(Customer.segment_id == segment.id)
            )
            or 0
        )
        if members < SEGMENT_MIN_SIZE:
            continue
        at_risk = (
            db.scalar(
                select(func.count(func.distinct(Prediction.customer_id))).where(
                    Prediction.prediction_type == "churn",
                    Prediction.probability >= CHURN_THRESHOLD,
                    Prediction.customer_id.in_(
                        select(Customer.id).where(Customer.segment_id == segment.id)
                    ),
                )
            )
            or 0
        )
        share = at_risk / members
        if share >= SEGMENT_RISK_SHARE:
            alerts.append(
                {
                    "alert_type": "segment_change",
                    "severity": "high",
                    "title": f"Segment at risk: {segment.name}",
                    "description": (
                        f"{share:.0%} of {members} members in {segment.name} show high "
                        f"churn risk ({at_risk} customers)."
                    ),
                    "evidence": {
                        "segment_id": segment.id,
                        "segment_name": segment.name,
                        "members": members,
                        "at_risk": at_risk,
                        "risk_share": round(share, 4),
                    },
                    "entity_type": "segment",
                    "entity_id": segment.id,
                    "dedup_key": f"segment:{segment.id}:{period}",
                }
            )
    return alerts


def detect_candidates(
    db: Session,
    reference_date: datetime | None = None,
) -> list[dict[str, Any]]:
    ref = normalize_reference_date(reference_date)
    period = _period_label(ref)
    candidates: list[dict[str, Any]] = []
    candidates.extend(_detect_churn_candidates(db, period))
    candidates.extend(_detect_revenue_anomaly(db, ref, period))
    candidates.extend(_detect_engagement_decline(db, ref, period))
    candidates.extend(_detect_new_opportunities(db, period))
    candidates.extend(_detect_segment_change(db, period))
    return candidates


def materialize_alerts(db: Session, reference_date: datetime | None = None) -> dict[str, Any]:
    """Insert new alerts, skipping existing dedup keys. Returns a report."""
    ref = normalize_reference_date(reference_date)
    candidates = detect_candidates(db, ref)
    if not candidates:
        return {
            "reference_date": ref.isoformat(),
            "evaluated": 0,
            "created": 0,
            "skipped_duplicates": 0,
        }
    existing = {
        row[0]
        for row in db.execute(
            select(Alert.dedup_key).where(
                Alert.dedup_key.in_([item["dedup_key"] for item in candidates])
            )
        ).all()
    }
    created = 0
    for item in candidates:
        if item["dedup_key"] in existing:
            continue
        db.add(Alert(**item))
        try:
            db.flush()
            created += 1
        except IntegrityError:
            db.rollback()
    db.commit()
    return {
        "reference_date": ref.isoformat(),
        "evaluated": len(candidates),
        "created": created,
        "skipped_duplicates": len(candidates) - created,
    }


def list_alerts(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    alert_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
) -> tuple[list[Alert], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc())
    if alert_type is not None:
        stmt = stmt.where(Alert.alert_type == alert_type)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if entity_type is not None:
        stmt = stmt.where(Alert.entity_type == entity_type)
    return paginate(stmt, db, page, page_size)


def get_alert(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise NotFoundError("Alert", alert_id)
    return alert


def acknowledge_alert(db: Session, alert_id: int) -> Alert:
    alert = get_alert(db, alert_id)
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return alert
