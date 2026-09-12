"""Deterministic opportunity scoring: no model, no randomness, fully explainable.

Each customer receives five component scores in [0, 1] — value, purchase
likelihood, retention need, engagement, momentum — combined with fixed
weights. Percentiles are ranked within the scored batch, so identical
inputs always produce identical scores. Every score carries its component
breakdown plus human-readable reasons naming the top drivers.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.analytics.base import percentile_rank
from app.analytics.features import CustomerFeatures

WEIGHTS: dict[str, float] = {
    "value": 0.30,
    "purchase": 0.25,
    "retention": 0.20,
    "engagement": 0.15,
    "momentum": 0.10,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "opportunity weights must sum to 1"


class OpportunityScore(BaseModel):
    customer_id: int
    score: float
    tier: str
    components: dict[str, float]
    reasons: list[str]


def score_tier(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


_COMPONENT_REASONS: dict[str, str] = {
    "value": "high lifetime value ({revenue:.0f} revenue)",
    "purchase": "likely to buy soon ({proba:.0%} purchase probability)",
    "retention": "needs retention attention ({proba:.0%} churn risk)",
    "engagement": "strongly engaged ({events:.0f} interactions)",
    "momentum": "positive recent momentum",
}


def score_customers(
    records: list[CustomerFeatures],
    churn_probabilities: dict[int, float],
    purchase_probabilities: dict[int, float],
) -> list[OpportunityScore]:
    """Score a batch deterministically; empty input yields an empty list."""
    if not records:
        return []
    revenues = [record.total_revenue for record in records]
    event_counts = [float(record.total_interactions) for record in records]

    scores: list[OpportunityScore] = []
    for record in records:
        churn = churn_probabilities.get(record.customer_id, 0.0)
        purchase = purchase_probabilities.get(record.customer_id, 0.0)
        components = {
            "value": percentile_rank(record.total_revenue, revenues),
            "purchase": purchase,
            "retention": churn,
            "engagement": percentile_rank(float(record.total_interactions), event_counts),
            "momentum": max(0.0, (record.order_trend_90d + record.interaction_trend_90d) / 2),
        }
        score = sum(components[name] * weight for name, weight in WEIGHTS.items())
        drivers = sorted(components, key=lambda name: (-components[name], name))[:2]
        reasons = []
        for name in drivers:
            if name == "value":
                reasons.append(_COMPONENT_REASONS[name].format(revenue=record.total_revenue))
            elif name == "purchase":
                reasons.append(_COMPONENT_REASONS[name].format(proba=purchase))
            elif name == "retention":
                reasons.append(_COMPONENT_REASONS[name].format(proba=churn))
            elif name == "engagement":
                reasons.append(_COMPONENT_REASONS[name].format(events=record.total_interactions))
            else:
                reasons.append(_COMPONENT_REASONS[name])
        scores.append(
            OpportunityScore(
                customer_id=record.customer_id,
                score=score,
                tier=score_tier(score),
                components=components,
                reasons=reasons,
            )
        )
    return scores
