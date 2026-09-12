"""AI context assembly: verified backend data shaped for LLM grounding.

Every builder reads from the existing analytics/ML services — never from
request-supplied numbers — so the model can only explain what the system
actually computed. Floats are rounded for compact, stable prompts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.llm import context as ctx
from app.services import customers as customer_service
from app.services import opportunities as opportunity_service
from app.services import overview as overview_service
from app.services import segments as segment_service


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, list):
        return [_round(item) for item in value]
    if isinstance(value, dict):
        return {key: _round(item) for key, item in value.items()}
    return value


def build_ai_context(db: Session, kind: str, entity_id: int | None) -> dict[str, Any]:
    """Assemble grounded context for an entity link. Raises NotFoundError
    for missing entities (mapped to 404 upstream)."""
    if kind == "overview":
        overview = overview_service.get_overview(db)
        health = {
            name: {"value": kpi["value"], "change_pct": kpi["change_pct"]}
            for name, kpi in overview.health.model_dump().items()
        }
        attention = [
            {"title": item.title, "severity": item.severity, "detail": item.description}
            for item in overview.attention
        ]
        return ctx.overview_context(
            _round({"kpis": health, "attention": attention}),
            [bucket.model_dump() for bucket in overview.trends],
        )
    if kind == "customer":
        assert entity_id is not None
        customer, metrics, predictions, opportunities = customer_service.get_customer_intelligence(
            db, entity_id
        )
        return ctx.customer_context(
            {
                "id": customer.id,
                "name": f"{customer.first_name} {customer.last_name}",
                "segment": customer.segment.name if customer.segment else None,
            },
            _round(metrics.model_dump(exclude_none=True)),
            [
                {
                    "type": prediction.prediction_type,
                    "probability": round(prediction.probability, 4),
                    "band": prediction.band,
                    "signals": prediction.signal_list(),
                }
                for prediction in predictions
            ],
            [
                {
                    "type": opportunity.opportunity_type,
                    "score": round(opportunity.score, 4),
                    "tier": opportunity.tier,
                    "reasons": opportunity.reason_list(),
                }
                for opportunity in opportunities
            ],
        )
    if kind == "segment":
        assert entity_id is not None
        segment = segment_service.get_segment(db, entity_id)
        members, _ = segment_service.list_segment_customers(db, entity_id, page_size=10)
        return ctx.segment_context(
            _round(
                {
                    "name": segment.name,
                    "size": segment.size,
                    "share": segment.share,
                    "avg_revenue": segment.avg_revenue,
                    "avg_recency_days": segment.avg_recency_days,
                    "avg_completed_orders": segment.avg_completed_orders,
                }
            ),
            [
                {"id": member.id, "name": f"{member.first_name} {member.last_name}"}
                for member in members
            ],
        )
    # kind == "opportunity"
    assert entity_id is not None
    opportunity = opportunity_service.get_opportunity(db, entity_id)
    customer, metrics, _, _ = customer_service.get_customer_intelligence(
        db, opportunity.customer_id
    )
    return ctx.opportunity_context(
        _round(
            {
                "type": opportunity.opportunity_type,
                "score": opportunity.score,
                "tier": opportunity.tier,
                "estimated_value": float(opportunity.estimated_value),
                "reasons": opportunity.reason_list(),
                "recommended_action": opportunity.recommended_action,
            }
        ),
        _round(
            {
                "customer_revenue": metrics.total_revenue,
                "customer_orders": metrics.completed_orders,
                "customer_recency_days": metrics.recency_days,
                "segment": customer.segment.name if customer.segment else None,
            }
        ),
    )
