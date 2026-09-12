"""Feature engineering tests: names, vectors, batch behavior, edge cases."""

import math
from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.analytics.features import (
    FEATURE_NAMES,
    build_customer_features,
    to_dataset,
    to_matrix,
)
from tests.analytics_helpers import REF, add_customer, add_event, add_product, add_txn, at
from tests.conftest import TestingSession


@pytest.fixture()
def db() -> Session:
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_feature_names_are_stable_and_complete() -> None:
    assert len(FEATURE_NAMES) == 47
    assert len(set(FEATURE_NAMES)) == 47
    assert FEATURE_NAMES[0] == "total_orders"
    assert "recency_days" in FEATURE_NAMES
    assert "purchase_conversion_rate" in FEATURE_NAMES
    assert "is_inactive_90d" in FEATURE_NAMES


def test_zero_activity_vector_is_finite_with_sentinels(db: Session, unique: str) -> None:
    customer = add_customer(db, unique, tag="zero")
    db.commit()

    (record,) = build_customer_features(db, REF, 365, [customer.id])
    vector = record.to_vector()
    assert len(vector) == len(FEATURE_NAMES)
    assert all(math.isfinite(value) for value in vector)
    assert record.recency_days == 365.0
    assert record.days_since_last_interaction == 365.0
    assert record.has_orders == 0.0
    assert record.has_interactions == 0.0
    assert record.is_inactive_90d == 1.0
    assert record.is_recently_active == 0.0


def test_active_customer_feature_values(db: Session, unique: str) -> None:
    product = add_product(db, unique, tag="feat")
    customer = add_customer(db, unique, tag="feat")
    add_txn(
        db,
        customer.id,
        product.id,
        at(date(2026, 8, 20), 10),
        quantity=2,
        unit_price=50.0,
    )
    add_txn(
        db,
        customer.id,
        product.id,
        at(date(2026, 8, 25), 10),
        quantity=1,
        unit_price=100.0,
    )
    add_event(
        db,
        customer.id,
        at(date(2026, 8, 26), 10),
        itype="purchase",
        channel="web",
    )
    db.commit()

    (record,) = build_customer_features(db, REF, 365, [customer.id])
    assert record.total_orders == 2
    assert record.completed_orders == 2
    assert record.total_revenue == 200.0
    assert record.avg_order_value == 100.0
    assert record.recency_days == 6.0
    assert record.has_orders == 1.0
    assert record.is_recently_active == 1.0
    assert record.is_inactive_90d == 0.0
    assert record.purchase_conversion_rate == 1.0
    assert record.interaction_per_order == 0.5
    assert record.distinct_products == 1
    assert all(math.isfinite(value) for value in record.to_vector())


def test_batch_generation_is_deterministic(db: Session, unique: str) -> None:
    product = add_product(db, unique, tag="batch")
    ids = []
    for tag in ("b1", "b2", "b3"):
        customer = add_customer(db, unique, tag=f"batch-{tag}")
        ids.append(customer.id)
    add_txn(
        db,
        ids[0],
        product.id,
        at(date(2026, 7, 1), 10),
        unit_price=30.0,
    )
    db.commit()

    first = build_customer_features(db, REF, 365, ids)
    second = build_customer_features(db, REF, 365, ids)
    assert [f.customer_id for f in first] == ids
    assert first == second


def test_matrix_and_dataset_conversion(db: Session, unique: str) -> None:
    customer = add_customer(db, unique, tag="conv")
    db.commit()

    features = build_customer_features(db, REF, 365, [customer.id])
    names, matrix = to_matrix(features)
    assert names == FEATURE_NAMES
    assert len(matrix) == 1
    assert len(matrix[0]) == len(FEATURE_NAMES)

    (row,) = to_dataset(features)
    assert row["customer_id"] == customer.id
    assert row["total_orders"] == 0.0
    assert set(row) == {"customer_id", *FEATURE_NAMES}


def test_history_window_changes_sentinels(db: Session, unique: str) -> None:
    customer = add_customer(db, unique, tag="win")
    db.commit()

    (short,) = build_customer_features(db, REF, 90, [customer.id])
    (long,) = build_customer_features(db, REF, 365, [customer.id])
    assert short.recency_days == 90.0
    assert long.recency_days == 365.0


def test_reference_date_excludes_future_orders(db: Session, unique: str) -> None:
    product = add_product(db, unique, tag="reffd")
    customer = add_customer(db, unique, tag="reffd")
    add_txn(
        db,
        customer.id,
        product.id,
        at(date(2026, 10, 1), 10),
        unit_price=500.0,
    )
    db.commit()

    (record,) = build_customer_features(db, REF, 365, [customer.id])
    assert record.total_orders == 0
    assert record.total_revenue == 0.0
    assert record.has_orders == 0.0
