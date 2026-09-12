"""Opportunity scoring tests: bounds, tiers, reproducibility, explanations."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.analytics.features import build_customer_features
from app.ml.opportunity import WEIGHTS, score_customers, score_tier

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


def test_weights_sum_to_one() -> None:
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    assert set(WEIGHTS) == {"value", "purchase", "retention", "engagement", "momentum"}


def test_tier_thresholds() -> None:
    assert score_tier(0.9) == "high"
    assert score_tier(0.7) == "high"
    assert score_tier(0.5) == "medium"
    assert score_tier(0.4) == "medium"
    assert score_tier(0.1) == "low"


def test_scoring_bounds_reasons_and_reproducibility(ml_db: Session) -> None:
    records = build_customer_features(ml_db, TRAIN_REF)
    churn = {record.customer_id: 0.8 for record in records}
    purchase = {record.customer_id: 0.2 for record in records}

    first = score_customers(records, churn, purchase)
    second = score_customers(records, churn, purchase)
    assert first == second
    assert len(first) == len(records)
    for score in first:
        assert 0.0 <= score.score <= 1.0
        assert score.tier == score_tier(score.score)
        assert set(score.components) == set(WEIGHTS)
        assert all(0.0 <= value <= 1.0 for value in score.components.values())
        assert len(score.reasons) == 2
        assert all(isinstance(reason, str) and reason for reason in score.reasons)


def test_empty_input_yields_empty_output() -> None:
    assert score_customers([], {}, {}) == []


def test_value_drives_ranking(ml_db: Session) -> None:
    records = build_customer_features(ml_db, TRAIN_REF)
    richest = max(records, key=lambda record: record.total_revenue)
    poorest = min(records, key=lambda record: record.total_revenue)
    assert richest.customer_id != poorest.customer_id
    flat = {record.customer_id: 0.5 for record in records}
    scores = {score.customer_id: score for score in score_customers(records, flat, flat)}
    assert scores[richest.customer_id].score >= scores[poorest.customer_id].score
