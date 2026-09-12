"""Seed tests: determinism, interconnection, idempotency, integrity, audit.

Generator tests are pure (no database). Seeder tests use the shared
in-memory SQLite database and always start from an explicit reset so they
are independent of test execution order.
"""

import pytest
from sqlalchemy.orm import Session

from app.seed.generator import SeedConfig, generate
from app.seed.seeder import SeedError, audit_dataset, seed_dataset, table_counts
from tests.conftest import TestingSession


@pytest.fixture()
def db() -> Session:
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def _tiny(seed: int = 7) -> SeedConfig:
    return SeedConfig(seed=seed, customers=100)


def test_generate_is_deterministic_for_same_triple() -> None:
    first = generate(_tiny())
    second = generate(_tiny())
    assert first == second


def test_generate_differs_by_seed_and_anchor() -> None:
    from datetime import date

    base = generate(_tiny(seed=7))
    assert generate(_tiny(seed=8)) != base
    moved_anchor = generate(SeedConfig(seed=7, customers=100, anchor=date(2026, 6, 1)))
    assert moved_anchor != base


def test_every_customer_has_transactions_and_valid_references() -> None:
    data = generate(_tiny())
    n_customers = len(data.customers)
    n_products = len(data.products)
    assert n_customers == 100
    assert len(data.campaigns) == 12
    assert len(data.products) >= 50

    seen_customers = {txn["customer_idx"] for txn in data.transactions}
    assert seen_customers == set(range(n_customers))
    assert all(0 <= txn["product_idx"] < n_products for txn in data.transactions)
    assert all(txn["quantity"] >= 1 for txn in data.transactions)
    assert all(txn["discount"] >= 0 for txn in data.transactions)
    assert all(
        event["campaign_idx"] is None or 0 <= event["campaign_idx"] < len(data.campaigns)
        for event in data.interactions
    )
    assert {event["customer_idx"] for event in data.interactions} <= set(range(n_customers))


def test_transaction_totals_are_computed_correctly() -> None:
    data = generate(_tiny())
    for txn in data.transactions[:500]:
        expected = round(txn["quantity"] * txn["unit_price"] - txn["discount"], 2)
        assert txn["total_amount"] == expected


def test_seed_refuses_when_data_exists(db: Session) -> None:
    seed_dataset(db, _tiny(), reset=True)
    with pytest.raises(SeedError):
        seed_dataset(db, _tiny(), reset=False)


def test_seed_reset_reproduces_identical_counts(db: Session) -> None:
    first = seed_dataset(db, _tiny(), reset=True)
    second = seed_dataset(db, _tiny(), reset=True)
    assert first["counts"] == second["counts"]
    assert first["counts"]["customers"] == 100
    assert first["counts"]["transactions"] > 0
    assert first["counts"]["interactions"] > 0


def test_audit_reports_zero_orphans_and_full_coverage(db: Session) -> None:
    seed_dataset(db, _tiny(), reset=True)
    counts = table_counts(db)
    audit = audit_dataset(db)
    assert audit["orphan_transactions"] == 0
    assert audit["orphan_interactions"] == 0
    assert audit["customers_with_orders"] == counts["customers"]
    assert audit["completed_revenue"] > 0
    assert audit["transaction_date_min"] <= audit["transaction_date_max"]
    assert set(audit["transaction_status_mix"]) <= {"completed", "pending", "refunded", "cancelled"}
    assert sum(audit["transaction_status_mix"].values()) == counts["transactions"]
    assert len(audit["transactions_by_category"]) > 1
