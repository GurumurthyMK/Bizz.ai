"""Business reports: deterministic sections always, LLM narrative optionally.

Facts (metrics, segments, predictions, opportunities, recommendations) come
exclusively from analytics/ML services. The LLM only writes the narrative
summary and narrative recommendations from a structured report context; when
it is unavailable the factual report is still complete and ``llm_available``
is False with null narrative fields.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.base import normalize_reference_date
from app.llm import context as ctx
from app.llm.provider import LLMConfigurationError, LLMError, LLMProvider, get_provider
from app.llm.service import answer_question, summarize
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.models.segment import Segment
from app.models.transaction import Transaction
from app.schemas.opportunity import OpportunityResponse
from app.schemas.prediction import PredictionResponse
from app.schemas.report import (
    RecommendationItem,
    ReportMeta,
    ReportNarrative,
    ReportOpportunityBlock,
    ReportPredictionBlock,
    ReportResponse,
)
from app.schemas.segment import SegmentResponse
from app.services import opportunities as opportunity_service
from app.services import overview as overview_service
from app.services import predictions as prediction_service
from app.services import segments as segment_service

RECOMMENDATION_QUESTIONS = (
    "What are the top 3 recommended business actions based on this report? "
    "Answer as a short numbered list using only the reported facts."
)


def _deterministic_summary(overview: Any) -> str:
    health = overview.health
    rev, cust, txns = health.revenue, health.active_customers, health.transactions
    return (
        f"In the trailing 30 days the business recorded ${rev.value:,.0f} revenue "
        f"({rev.change_pct if rev.change_pct is not None else 'n/a'}% vs prior period) "
        f"across {txns.value:,.0f} transactions from {cust.value:,.0f} active customers. "
        f"{len(overview.attention)} item(s) need attention and "
        f"{len(overview.opportunities)} scored opportunit(ies) are open."
    )


def _deterministic_recommendations(
    overview: Any,
    churn_high: int,
    revenue_at_risk: float,
    top_opportunity: OpportunityResponse | None,
    segments: list[Segment],
) -> list[RecommendationItem]:
    recommendations: list[RecommendationItem] = []
    if churn_high > 0:
        recommendations.append(
            RecommendationItem(
                title=f"Retain {churn_high} high-risk customers",
                detail=(
                    f"Model-flagged churn risk exposes ${revenue_at_risk:,.0f} in "
                    "lifetime revenue. Prioritize retention outreach now."
                ),
                priority="high",
            )
        )
    revenue = overview.health.revenue
    if revenue.direction == "down" and revenue.change_pct is not None:
        recommendations.append(
            RecommendationItem(
                title="Investigate the revenue decline",
                detail=(
                    f"Revenue is {revenue.change_pct:.1f}% below the prior 30 days. "
                    "Review the steepest segments and recent churn signals."
                ),
                priority="high",
            )
        )
    if top_opportunity is not None:
        recommendations.append(
            RecommendationItem(
                title=f"Pursue top {top_opportunity.opportunity_type} opportunity",
                detail=(
                    f"Customer {top_opportunity.customer_id} scores "
                    f"{top_opportunity.score:.0%} with estimated value "
                    f"${float(top_opportunity.estimated_value):,.0f}. "
                    f"{top_opportunity.recommended_action}"
                ),
                priority="medium",
            )
        )
    if segments:
        biggest = max(segments, key=lambda segment: segment.size)
        recommendations.append(
            RecommendationItem(
                title=f"Review segment {biggest.name}",
                detail=(
                    f"Largest segment holds {biggest.size:,} customers "
                    f"averaging ${biggest.avg_revenue:,.0f} revenue."
                ),
                priority="low",
            )
        )
    return recommendations[:5]


def _resolve_provider(explicit: LLMProvider | None) -> LLMProvider | None:
    if explicit is not None:
        return explicit
    try:
        return get_provider()
    except LLMConfigurationError:
        return None


def generate_report(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    artifacts_dir: Path | None = None,
    llm_provider: LLMProvider | None = None,
) -> ReportResponse:
    ref = normalize_reference_date(reference_date)
    overview = overview_service.get_overview(db, ref, history_days, artifacts_dir=artifacts_dir)

    segments = segment_service.list_segments(db)

    churn_items, _ = prediction_service.list_predictions(
        db, page=1, page_size=5, prediction_type="churn", sort_by="probability", order="desc"
    )
    purchase_items, _ = prediction_service.list_predictions(
        db, page=1, page_size=5, prediction_type="purchase", sort_by="probability", order="desc"
    )

    # Count high-band predictions with a single aggregate each.
    def _band_count(prediction_type: str, band: str) -> int:
        return (
            db.scalar(
                select(func.count())
                .select_from(Prediction)
                .where(Prediction.prediction_type == prediction_type, Prediction.band == band)
            )
            or 0
        )

    churn_high_count = _band_count("churn", "high")
    purchase_high_count = _band_count("purchase", "high")

    top_opportunities, opportunity_total = opportunity_service.list_opportunities(
        db, page=1, page_size=10, sort_by="score", order="desc"
    )
    high_count = (
        db.scalar(select(func.count()).select_from(Opportunity).where(Opportunity.tier == "high"))
        or 0
    )

    # Revenue at risk from churn-high customers' lifetime revenue.
    churn_ids = [
        item.customer_id
        for item in prediction_service.list_predictions(
            db, page=1, page_size=1000, prediction_type="churn", band="high"
        )[0]
    ]
    revenue_at_risk_value = (
        float(
            db.scalar(
                select(func.coalesce(func.sum(Transaction.total_amount), 0)).where(
                    Transaction.customer_id.in_(churn_ids),
                    Transaction.status == "completed",
                )
            )
            or 0
        )
        if churn_ids
        else 0.0
    )

    top_opportunity = (
        OpportunityResponse.model_validate(top_opportunities[0]) if top_opportunities else None
    )
    recommendations = _deterministic_recommendations(
        overview, churn_high_count, revenue_at_risk_value, top_opportunity, segments
    )

    provider = _resolve_provider(llm_provider)
    narrative = ReportNarrative()
    llm_available = provider is not None
    if provider is not None:
        report_context = ctx.business_context(
            "overview",
            {
                "reference_date": ref.isoformat(),
                "executive_summary": _deterministic_summary(overview),
                "key_metrics": overview.health.model_dump(),
                "attention": [
                    {"title": item.title, "severity": item.severity} for item in overview.attention
                ],
                "top_opportunities": [
                    {
                        "customer_id": item.customer_id,
                        "score": round(item.score, 4),
                        "type": item.opportunity_type,
                    }
                    for item in top_opportunities[:5]
                ],
                "recommendations": [
                    {"title": item.title, "detail": item.detail} for item in recommendations
                ],
            },
        )
        try:
            summary_result = summarize(report_context, provider=provider)
            actions_result = answer_question(
                report_context, RECOMMENDATION_QUESTIONS, provider=provider
            )
            narrative = ReportNarrative(
                executive_summary=summary_result.text,
                recommendations=actions_result.text,
                model=summary_result.model,
                provider=summary_result.provider,
            )
        except LLMError:
            llm_available = False

    return ReportResponse(
        meta=ReportMeta(
            reference_date=ref.isoformat(),
            history_days=history_days,
            llm_available=llm_available,
            customer_count=overview.meta.customer_count,
        ),
        executive_summary=_deterministic_summary(overview),
        key_metrics=overview.health,
        customer_trends=overview.trends,
        segments=[SegmentResponse.model_validate(item) for item in segments],
        predictions=ReportPredictionBlock(
            churn_high_count=churn_high_count,
            purchase_high_count=purchase_high_count,
            top_churn=[PredictionResponse.model_validate(item) for item in churn_items],
            top_purchase=[PredictionResponse.model_validate(item) for item in purchase_items],
        ),
        opportunities=ReportOpportunityBlock(
            total=opportunity_total,
            high_count=high_count,
            top=[OpportunityResponse.model_validate(item) for item in top_opportunities],
        ),
        recommendations=recommendations,
        narrative=narrative,
    )
