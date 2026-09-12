"""Analytics tests: base utilities, RFM, customers, products, campaigns.

Uses the shared in-memory SQLite database with explicit customer/product
scoping, so tests stay isolated despite the shared session store.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.analytics import base, campaigns, customers, products, rfm
from tests.analytics_helpers import (
    REF,
    add_campaign,
    add_customer,
    add_event,
    add_product,
    add_txn,
)
from tests.conftest import TestingSession


@pytest.fixture()
def db() -> Session:
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def at(day: date, hour: int = 10) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Base utilities
# ---------------------------------------------------------------------------


def test_normalize_reference_date() -> None:
    assert base.normalize_reference_date(None).tzinfo is not None
    assert base.normalize_reference_date(date(2026, 9, 1)) == datetime(2026, 9, 1, tzinfo=UTC)
    naive = datetime(2026, 9, 1, 12, 0)
    assert base.normalize_reference_date(naive) == naive.replace(tzinfo=UTC)


def test_window_bounds_and_validation() -> None:
    start, end = base.window_bounds(datetime(2026, 9, 1, tzinfo=UTC), 30)
    assert (end - start).days == 30
    with pytest.raises(ValueError):
        base.window_bounds(None, 0)


def test_safe_math_helpers() -> None:
    assert base.safe_div(5.0, 2.0) == 2.5
    assert base.safe_div(1.0, 0.0) == 0.0
    assert base.safe_div(1.0, 0.0, default=-1.0) == -1.0
    assert base.normalized_diff(3.0, 1.0) == 0.5
    assert base.normalized_diff(0.0, 0.0) == 0.0
    assert base.normalized_diff(0.0, 5.0) == -1.0
    assert base.percentile_rank(2.0, [1.0, 2.0, 3.0]) == pytest.approx(2 / 3)
    assert base.percentile_rank(9.0, []) == 0.0
    assert base.quantile_breaks([], 5) == []
    with pytest.raises(ValueError):
        base.quantile_breaks([1.0], 1)
    breaks = base.quantile_breaks([float(i) for i in range(1, 11)], 5)
    assert breaks == sorted(breaks) and len(breaks) == 4
    assert base.assign_bin(0.0, breaks) == 0
    assert base.assign_bin(99.0, breaks) == 4
    assert base.quintile_score(0, 10) == 1
    assert base.quintile_score(9, 10) == 5
    assert base.quintile_score(0, 10, invert=True) == 5
    assert base.quintile_score(0, 1, invert=True) == 5
    with pytest.raises(ValueError):
        base.quintile_score(0, 0)


# ---------------------------------------------------------------------------
# RFM classification tables
# ---------------------------------------------------------------------------


def test_classify_segment_covers_expected_cases() -> None:
    assert rfm.classify_segment(5, 1) == "New"
    assert rfm.classify_segment(5, 5) == "Champions"
    assert rfm.classify_segment(4, 4) == "Champions"
    assert rfm.classify_segment(3, 3) == "Loyal"
    assert rfm.classify_segment(3, 5) == "Loyal"
    assert rfm.classify_segment(5, 2) == "Potential Loyalists"
    assert rfm.classify_segment(4, 1) == "Potential Loyalists"
    assert rfm.classify_segment(1, 5) == "Cannot Lose Them"
    assert rfm.classify_segment(2, 4) == "Cannot Lose Them"
    assert rfm.classify_segment(3, 2) == "Emerging"
    assert rfm.classify_segment(3, 1) == "Emerging"
    assert rfm.classify_segment(2, 2) == "At Risk"
    assert rfm.classify_segment(2, 1) == "At Risk"
    assert rfm.classify_segment(1, 3) == "Lost"
    assert rfm.classify_segment(1, 1) == "Lost"
    assert rfm.classify_value_tier(5) == "High Value"
    assert rfm.classify_value_tier(4) == "High Value"
    assert rfm.classify_value_tier(3) == "Medium Value"
    assert rfm.classify_value_tier(2) == "Low Value"
    assert rfm.classify_value_tier(1) == "Low Value"


def test_compute_rfm_hand_checked_scores(db: Session, unique: str) -> None:
    p = add_product(db, unique, tag="rfm")
    customers = {}
    specs = [
        ("ra", 10, date(2026, 8, 30), 100.0),
        ("rb", 5, date(2026, 8, 25), 100.0),
        ("rc", 5, date(2026, 8, 15), 60.0),
        ("rd", 2, date(2026, 7, 1), 50.0),
    ]
    for tag, orders, last_day, price in specs:
        customer = add_customer(db, unique, tag=f"rfm-{tag}")
        customers[tag] = customer
        for i in range(orders):
            day = last_day - timedelta(days=i * 7)
            add_txn(db, customer.id, p.id, at(day), unit_price=price)
    quiet = add_customer(db, unique, tag="rfm-re")
    db.commit()

    ids = [customers[t].id for t, _, _, _ in specs] + [quiet.id]
    records = {r.customer_id: r for r in rfm.compute_rfm(db, REF, 365, ids)}

    assert (records[customers["ra"].id].r_score, records[customers["ra"].id].f_score) == (5, 5)
    assert records[customers["ra"].id].segment == "Champions"
    assert records[customers["rb"].id].r_score == 4
    assert records[customers["rb"].id].f_score == 3
    assert records[customers["rb"].id].segment == "Loyal"
    assert records[customers["rc"].id].segment == "Loyal"
    assert records[customers["rd"].id].segment == "At Risk"
    assert records[quiet.id].segment == "Lost"
    assert records[quiet.id].value_tier == "Low Value"
    assert records[quiet.id].recency_days is None
    assert records[customers["ra"].id].value_tier == "High Value"


def test_compute_rfm_empty_and_deterministic(db: Session, unique: str) -> None:
    assert rfm.compute_rfm(db, REF, 365, []) == []
    p = add_product(db, unique, tag="rfmd")
    c = add_customer(db, unique, tag="rfmd")
    add_txn(db, c.id, p.id, at(date(2026, 8, 20)), unit_price=50.0)
    db.commit()
    first = rfm.compute_rfm(db, REF, 365, [c.id])
    second = rfm.compute_rfm(db, REF, 365, [c.id])
    assert first == second
    assert len(first) == 1


# ---------------------------------------------------------------------------
# Customer metrics
# ---------------------------------------------------------------------------


def test_customer_metrics_unknown_id_yields_zero_row(db: Session) -> None:
    (metrics,) = customers.compute_customer_metrics(db, REF, 365, [-1])
    assert metrics.total_orders == 0
    assert metrics.total_revenue == 0.0
    assert metrics.recency_days is None
    assert metrics.is_inactive_90d is True
    assert metrics.refund_rate == 0.0


def test_customer_metrics_hand_checked(db: Session, unique: str) -> None:
    p1 = add_product(db, unique, tag="cm1", category="Gadgets")
    p2 = add_product(db, unique, tag="cm2", category="Apparel")
    c = add_customer(db, unique, tag="cm")
    add_txn(db, c.id, p1.id, at(date(2026, 1, 10)), unit_price=100.0)
    add_txn(db, c.id, p2.id, at(date(2026, 2, 10)), unit_price=200.0)
    add_txn(db, c.id, p1.id, at(date(2026, 3, 10)), unit_price=300.0)
    add_txn(db, c.id, p1.id, at(date(2026, 3, 11)), unit_price=50.0, status="refunded")
    add_event(db, c.id, at(date(2026, 8, 20)), itype="open", channel="email")
    add_event(db, c.id, at(date(2026, 8, 21)), itype="click", channel="email")
    db.commit()

    metrics = customers.get_customer_metrics(db, c.id, REF, 365)
    assert metrics.total_orders == 4
    assert metrics.completed_orders == 3
    assert metrics.refunded_orders == 1
    assert metrics.total_revenue == 600.0
    assert metrics.avg_order_value == 200.0
    assert metrics.max_order_value == 300.0
    assert metrics.min_order_value == 100.0
    assert metrics.active_span_days == 59
    assert metrics.avg_days_between_orders == pytest.approx(29.5)
    assert metrics.recency_days == 174
    assert metrics.is_inactive_90d is True
    assert metrics.orders_last_180d == 1
    assert metrics.orders_last_90d == 0
    assert metrics.order_trend_90d == -1.0
    assert metrics.revenue_trend_90d == -1.0
    assert metrics.distinct_products == 2
    assert metrics.distinct_categories == 2
    assert metrics.favorite_category == "Gadgets"
    assert metrics.favorite_category_share == pytest.approx(400.0 / 600.0)
    assert metrics.refund_rate == pytest.approx(0.25)
    assert metrics.total_interactions == 2
    assert metrics.browse_interactions == 2
    assert metrics.days_since_last_interaction == 10


def test_customer_metrics_respects_reference_date(db: Session, unique: str) -> None:
    p = add_product(db, unique, tag="ref")
    c = add_customer(db, unique, tag="ref")
    add_txn(db, c.id, p.id, at(date(2026, 8, 15)), unit_price=40.0)
    add_txn(db, c.id, p.id, at(date(2026, 10, 5)), unit_price=999.0)
    add_txn(db, c.id, p.id, at(date(2025, 6, 1)), unit_price=777.0)
    db.commit()

    metrics = customers.get_customer_metrics(db, c.id, REF, 365)
    assert metrics.completed_orders == 1
    assert metrics.total_revenue == 40.0


def test_customer_metrics_no_purchases_with_interactions(db: Session, unique: str) -> None:
    c = add_customer(db, unique, tag="nop")
    add_event(db, c.id, at(date(2026, 8, 1)), itype="visit", channel="web")
    db.commit()

    metrics = customers.get_customer_metrics(db, c.id, REF, 365)
    assert metrics.completed_orders == 0
    assert metrics.avg_order_value == 0.0
    assert metrics.recency_days is None
    assert metrics.total_interactions == 1
    assert metrics.distinct_interaction_types == 1


# ---------------------------------------------------------------------------
# Product metrics
# ---------------------------------------------------------------------------


def test_product_metrics_empty_and_aggregates(db: Session, unique: str) -> None:
    p = add_product(db, unique, tag="pm")
    (empty,) = products.compute_product_metrics(db, REF, 365, [p.id])
    assert empty.units_sold == 0
    assert empty.last_sale_date is None
    assert empty.refund_rate == 0.0

    c = add_customer(db, unique, tag="pm")
    add_txn(db, c.id, p.id, at(date(2026, 8, 20)), quantity=2, unit_price=25.0)
    add_txn(db, c.id, p.id, at(date(2026, 5, 1)), quantity=1, unit_price=25.0)
    add_txn(db, c.id, p.id, at(date(2026, 6, 1)), unit_price=25.0, status="refunded")
    db.commit()

    (metrics,) = products.compute_product_metrics(db, REF, 365, [p.id])
    assert metrics.units_sold == 3
    assert metrics.revenue == 75.0
    assert metrics.orders == 2
    assert metrics.distinct_customers == 1
    assert metrics.refund_count == 1
    assert metrics.refund_rate == pytest.approx(1 / 3)
    assert metrics.recent_units_30d == 2
    assert metrics.last_sale_date is not None


def test_category_brand_summaries_and_top(db: Session, unique: str) -> None:
    cat_a, cat_b, brand = f"Gad-{unique}", f"App-{unique}", f"Brand-{unique}"
    p1 = add_product(db, unique, tag="top1", category=cat_a, brand=brand)
    p2 = add_product(db, unique, tag="top2", category=cat_a, brand=brand)
    p3 = add_product(db, unique, tag="top3", category=cat_b, brand=brand)
    c = add_customer(db, unique, tag="top")
    add_txn(db, c.id, p1.id, at(date(2026, 8, 1)), unit_price=100.0)
    add_txn(db, c.id, p2.id, at(date(2026, 8, 1)), unit_price=100.0)
    db.commit()

    summaries = {s.category: s for s in products.summarize_by_category(db, REF, 365)}
    assert summaries[cat_a].revenue == 200.0
    assert summaries[cat_b].revenue == 0.0
    assert summaries[cat_b].products >= 1

    brands = {s.brand: s for s in products.summarize_by_brand(db, REF, 365)}
    assert brands[brand].orders == 2

    metrics = products.compute_product_metrics(db, REF, 365, [p1.id, p2.id, p3.id])
    top = products.top_products(metrics, by="revenue", limit=2)
    assert [m.product_id for m in top] == [p1.id, p2.id]


# ---------------------------------------------------------------------------
# Campaign metrics
# ---------------------------------------------------------------------------


def test_campaign_metrics_funnel_and_roi(db: Session, unique: str) -> None:
    p = add_product(db, unique, tag="camp")
    camp = add_campaign(db, unique, tag="camp", budget=1000.00)
    x = add_customer(db, unique, tag="campx")
    y = add_customer(db, unique, tag="campy")
    add_event(db, x.id, at(date(2026, 8, 10)), itype="open", channel="email", campaign_id=camp.id)
    add_event(db, x.id, at(date(2026, 8, 11)), itype="click", channel="email", campaign_id=camp.id)
    add_event(db, x.id, at(date(2026, 8, 12)), itype="purchase", channel="web", campaign_id=camp.id)
    add_event(db, y.id, at(date(2026, 8, 10)), itype="open", channel="email", campaign_id=camp.id)
    add_event(db, y.id, at(date(2026, 8, 13)), itype="visit", channel="web")
    add_txn(db, x.id, p.id, at(date(2026, 8, 12)), unit_price=100.0)
    db.commit()

    (metrics,) = campaigns.compute_campaign_metrics(db, [camp.id])
    assert metrics.reached == 2
    assert metrics.opened == 2
    assert metrics.clicked == 1
    assert metrics.converted == 1
    assert metrics.open_rate == 1.0
    assert metrics.click_rate == 0.5
    assert metrics.click_to_open_rate == 0.5
    assert metrics.conversion_rate == 0.5
    assert metrics.attributed_revenue == 100.0
    assert metrics.roi == pytest.approx(-0.9)


def test_campaign_metrics_empty_and_comparison(db: Session, unique: str) -> None:
    quiet = add_campaign(db, unique, tag="quiet", budget=None)
    broke = add_campaign(db, unique, tag="broke", budget=0.0)
    db.commit()

    metrics = {
        m.campaign_id: m for m in campaigns.compute_campaign_metrics(db, [quiet.id, broke.id])
    }
    assert metrics[quiet.id].reached == 0
    assert metrics[quiet.id].open_rate is None
    assert metrics[quiet.id].roi is None
    assert metrics[broke.id].roi is None

    ranked = campaigns.compare_campaigns(list(metrics.values()))
    assert [m.campaign_id for m in ranked] == [quiet.id, broke.id]
    assert campaigns.compute_campaign_metrics(db, [-1]) == []
