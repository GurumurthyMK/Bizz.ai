"""Overview service: one coherent business-health payload from real data.

Composes the analytics layer (aggregates, trends, RFM-grade feature
signals) with the persisted ML models (churn/purchase probabilities,
opportunity scores). When model artifacts are absent, ML-driven sections
degrade honestly: ``ml_available`` is False, opportunities are empty, and
attention falls back to analytics-only signals. Nothing is ever invented.

Query discipline: aggregate SQL only (window rollups, trend buckets, one
feature batch); per-customer work happens in memory. No N+1 patterns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.analytics.base import normalize_reference_date
from app.analytics.features import build_customer_features
from app.ml.churn import load_churn
from app.ml.opportunity import score_customers
from app.ml.persistence import ModelNotTrainedError, load_bundle
from app.ml.purchase import load_purchase
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.transaction import Transaction
from app.schemas.overview import (
    AttentionItem,
    BusinessHealth,
    InvestigationLink,
    KpiValue,
    OpportunityItem,
    OverviewMeta,
    OverviewResponse,
    TrendBucket,
)

WINDOW_DAYS = 30
TREND_BUCKETS = 6
HIGH_RISK_THRESHOLD = 2 / 3


def _kpi(label: str, current: float, previous: float) -> KpiValue:
    if previous == 0:
        change = None
        direction = "up" if current > 0 else "flat"
    else:
        change = round((current - previous) / abs(previous) * 100, 1)
        direction = "up" if change > 0 else ("down" if change < 0 else "flat")
    return KpiValue(
        label=label,
        value=current,
        previous_value=previous,
        change_pct=change,
        direction=direction,
    )


def _window_rollup(db: Session, start: datetime, end: datetime) -> dict[str, float]:
    """Completed-transaction rollup for one window: revenue, orders, customers, refunds."""
    completed = Transaction.status == "completed"
    row = db.execute(
        select(
            func.coalesce(func.sum(case((completed, Transaction.total_amount), else_=0)), 0),
            func.sum(case((completed, 1), else_=0)),
            func.count(func.distinct(case((completed, Transaction.customer_id)))),
            func.sum(case((Transaction.status == "refunded", 1), else_=0)),
        ).where(Transaction.transaction_date >= start, Transaction.transaction_date <= end)
    ).one()
    return {
        "revenue": float(row[0] or 0),
        "orders": int(row[1] or 0),
        "customers": int(row[2] or 0),
        "refunds": int(row[3] or 0),
    }


def _interaction_count(db: Session, start: datetime, end: datetime) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Interaction)
            .where(Interaction.occurred_at >= start, Interaction.occurred_at <= end)
        )
        or 0
    )


def _section_link(label: str, href: str) -> InvestigationLink:
    return InvestigationLink(label=label, href=href, kind="section")


def _customer_link(customer_id: int) -> InvestigationLink:
    return InvestigationLink(
        label=f"Customer {customer_id}", href=f"/customers/{customer_id}", kind="entity"
    )


def get_overview(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    artifacts_dir: Path | None = None,
    attention_limit: int = 5,
    opportunity_limit: int = 5,
) -> OverviewResponse:
    ref = normalize_reference_date(reference_date)
    cur_start = ref - timedelta(days=WINDOW_DAYS)
    prev_start = ref - timedelta(days=2 * WINDOW_DAYS)

    current = _window_rollup(db, cur_start, ref)
    previous = _window_rollup(db, prev_start, cur_start)

    health = BusinessHealth(
        revenue=_kpi("Revenue", current["revenue"], previous["revenue"]),
        active_customers=_kpi("Active customers", current["customers"], previous["customers"]),
        transactions=_kpi("Transactions", current["orders"], previous["orders"]),
        avg_order_value=_kpi(
            "Average order value",
            current["revenue"] / current["orders"] if current["orders"] else 0.0,
            previous["revenue"] / previous["orders"] if previous["orders"] else 0.0,
        ),
    )

    trends: list[TrendBucket] = []
    bucket_stats: list[dict] = []
    for index in range(TREND_BUCKETS):
        end = ref - timedelta(days=index * WINDOW_DAYS)
        start = end - timedelta(days=WINDOW_DAYS)
        rollup = _window_rollup(db, start, end)
        interactions = _interaction_count(db, start, end)
        bucket_stats.append({**rollup, "interactions": interactions})
        trends.append(
            TrendBucket(
                period_start=start.isoformat(),
                period_end=end.isoformat(),
                revenue=rollup["revenue"],
                orders=rollup["orders"],
                active_customers=rollup["customers"],
                interactions=interactions,
            )
        )

    customer_count = db.scalar(select(func.count()).select_from(Customer)) or 0
    records = build_customer_features(db, ref, history_days)

    try:
        churn_model = load_churn(load_bundle("churn", artifacts_dir))
        purchase_model = load_purchase(load_bundle("purchase", artifacts_dir))
        ml_available = True
    except ModelNotTrainedError:
        churn_model = None
        purchase_model = None
        ml_available = False

    churn_scores: dict[int, float] = {}
    purchase_scores: dict[int, float] = {}
    if ml_available and records:
        assert churn_model is not None and purchase_model is not None
        churn_scores = {
            score.customer_id: score.churn_probability
            for score in churn_model.score_customers(records)
        }
        purchase_scores = {
            score.customer_id: score.purchase_probability
            for score in purchase_model.score_customers(records)
        }

    attention: list[AttentionItem] = []

    if ml_available and churn_scores:
        high_risk = sorted(
            (cid for cid, proba in churn_scores.items() if proba >= HIGH_RISK_THRESHOLD)
        )
        if high_risk:
            high_risk_set = set(high_risk)
            revenue_at_risk = sum(
                record.total_revenue for record in records if record.customer_id in high_risk_set
            )
            attention.append(
                AttentionItem(
                    id="high-churn-risk",
                    severity="high",
                    title="High churn-risk population",
                    description=(
                        f"{len(high_risk)} customers show high churn risk "
                        f"(${revenue_at_risk:,.0f} lifetime revenue exposed)."
                    ),
                    affected_customers=len(high_risk),
                    metric_value=round(revenue_at_risk, 2),
                    metric_label="revenue at risk",
                    links=[_customer_link(customer_id) for customer_id in high_risk[:3]]
                    + [_section_link("Predictions", "/predictions")],
                )
            )
    else:
        inactive = [record for record in records if record.is_inactive_90d == 1.0]
        if inactive:
            attention.append(
                AttentionItem(
                    id="inactive-customers",
                    severity="medium",
                    title="Inactive customer base",
                    description=(
                        f"{len(inactive)} customers have no orders in 90+ days. "
                        "Churn model unavailable; re-train to quantify risk."
                    ),
                    affected_customers=len(inactive),
                    links=[_section_link("Customers", "/customers")],
                )
            )

    revenue_change = health.revenue.change_pct
    if revenue_change is not None and revenue_change < -5:
        attention.append(
            AttentionItem(
                id="revenue-decline",
                severity="high" if revenue_change <= -15 else "medium",
                title="Revenue declining",
                description=(
                    f"Revenue {revenue_change:.1f}% vs the previous 30 days "
                    f"(${current['revenue']:,.0f} vs ${previous['revenue']:,.0f})."
                ),
                affected_customers=current["customers"],
                metric_value=revenue_change,
                metric_label="revenue change %",
                links=[_section_link("Insights", "/insights")],
            )
        )

    interactions_cur = bucket_stats[0]["interactions"]
    interactions_prev = bucket_stats[1]["interactions"]
    if interactions_prev > 0:
        engagement_change = (interactions_cur - interactions_prev) / interactions_prev * 100
        if engagement_change < -10:
            attention.append(
                AttentionItem(
                    id="engagement-decline",
                    severity="medium",
                    title="Engagement declining",
                    description=(
                        f"Customer interactions {engagement_change:.1f}% vs the previous "
                        f"30 days ({interactions_cur:,} vs {interactions_prev:,})."
                    ),
                    affected_customers=current["customers"],
                    metric_value=round(engagement_change, 1),
                    metric_label="interaction change %",
                    links=[_section_link("Insights", "/insights")],
                )
            )

    if current["refunds"] >= 5 and current["refunds"] >= 2 * previous["refunds"]:
        attention.append(
            AttentionItem(
                id="refund-spike",
                severity="medium",
                title="Refund spike",
                description=(
                    f"{current['refunds']} refunds in the last 30 days "
                    f"vs {previous['refunds']} in the prior period."
                ),
                affected_customers=current["customers"],
                metric_value=float(current["refunds"]),
                metric_label="refunds (30d)",
                links=[_section_link("Customers", "/customers")],
            )
        )

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    attention.sort(key=lambda item: (severity_rank[item.severity], -item.affected_customers))
    attention = attention[: max(0, attention_limit)]

    opportunities: list[OpportunityItem] = []
    if ml_available and records:
        scored = score_customers(records, churn_scores, purchase_scores)
        scored.sort(key=lambda item: (-item.score, item.customer_id))
        for item in scored[: max(0, opportunity_limit)]:
            opportunities.append(
                OpportunityItem(
                    customer_id=item.customer_id,
                    score=item.score,
                    tier=item.tier,
                    reasons=item.reasons,
                    links=[
                        _customer_link(item.customer_id),
                        _section_link("Opportunities", "/opportunities"),
                    ],
                )
            )

    return OverviewResponse(
        meta=OverviewMeta(
            reference_date=ref.isoformat(),
            history_days=history_days,
            ml_available=ml_available,
            customer_count=customer_count,
        ),
        health=health,
        trends=trends,
        attention=attention,
        opportunities=opportunities,
    )
