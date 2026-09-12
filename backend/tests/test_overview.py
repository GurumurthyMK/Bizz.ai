"""Overview tests: schema, calculations, empty/populated data, ref dates, links.

Populated tests run against the isolated seeded ``ml_db`` database with tiny
models trained into a temporary artifacts directory — the same integrated
path as production, minus scale.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.transaction import Transaction
from app.services import overview as overview_service

REF = "2026-09-01T00:00:00Z"
REF_DT = datetime(2026, 9, 1, tzinfo=UTC)
TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)

KNOWN_SECTIONS = {
    "/customers",
    "/segments",
    "/predictions",
    "/opportunities",
    "/insights",
    "/overview",
}


@pytest.fixture(scope="module")
def trained_dir(tmp_path_factory, ml_db: Session):  # type: ignore[no-untyped-def]
    from app.ml.churn import bundle_churn, train_churn
    from app.ml.persistence import save_bundle
    from app.ml.purchase import bundle_purchase, train_purchase

    directory = tmp_path_factory.mktemp("overview-artifacts")
    churn_model, churn_metrics = train_churn(ml_db, TRAIN_REF)
    save_bundle("churn", bundle_churn(churn_model, churn_metrics), directory)
    purchase_model, purchase_metrics = train_purchase(ml_db, TRAIN_REF)
    save_bundle("purchase", bundle_purchase(purchase_model, purchase_metrics), directory)
    return directory


@pytest.fixture(scope="module")
def api_client(ml_db: Session):  # type: ignore[no-untyped-def]
    engine = ml_db.get_bind()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app()

    def override():  # type: ignore[no-untyped-def]
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "overview-owner@example.com", "password": "s3cure-pass"},
    )
    assert response.status_code == 201
    yield client
    app.dependency_overrides.clear()


def test_overview_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/overview").status_code == 401


def test_overview_schema_and_meta(api_client: TestClient, trained_dir) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get("/api/v1/overview", params={"reference_date": REF})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"meta", "health", "trends", "attention", "opportunities"}
    assert body["meta"]["history_days"] == 365
    assert body["meta"]["customer_count"] == 300
    assert set(body["health"]) == {"revenue", "transactions", "active_customers", "avg_order_value"}
    assert len(body["trends"]) == 6
    for bucket in body["trends"]:
        assert set(bucket) >= {"period_start", "period_end", "revenue", "orders"}
    for item in body["attention"]:
        assert item["severity"] in ("high", "medium", "low")
        assert item["affected_customers"] >= 0
    scores = [item["score"] for item in body["opportunities"]]
    assert scores == sorted(scores, reverse=True)
    assert len(scores) <= 5


def test_overview_calculations_match_data(api_client: TestClient, ml_db: Session) -> None:  # type: ignore[no-untyped-def]
    body = api_client.get("/api/v1/overview", params={"reference_date": REF}).json()

    window_start = REF_DT.replace(tzinfo=None) - timedelta(days=30)
    expected_revenue = ml_db.scalar(
        select(func.coalesce(func.sum(Transaction.total_amount), 0)).where(
            Transaction.status == "completed",
            Transaction.transaction_date >= window_start,
            Transaction.transaction_date <= REF_DT.replace(tzinfo=None),
        )
    )
    assert body["health"]["revenue"]["value"] == float(expected_revenue or 0)

    revenue = body["health"]["revenue"]
    previous = revenue["previous_value"]
    if previous != 0:
        expected_change = round((revenue["value"] - previous) / abs(previous) * 100, 1)
        assert revenue["change_pct"] == expected_change

    aov = body["health"]["avg_order_value"]
    txns = body["health"]["transactions"]["value"]
    if txns:
        assert aov["value"] == revenue["value"] / txns

    trend_revenue = sum(bucket["revenue"] for bucket in body["trends"])
    trend_start = REF_DT.replace(tzinfo=None) - timedelta(days=180)
    window_total = ml_db.scalar(
        select(func.coalesce(func.sum(Transaction.total_amount), 0)).where(
            Transaction.status == "completed",
            Transaction.transaction_date >= trend_start,
            Transaction.transaction_date <= REF_DT.replace(tzinfo=None),
        )
    )
    assert trend_revenue == float(window_total or 0)


def test_overview_reference_date_changes_results(api_client: TestClient) -> None:  # type: ignore[no-untyped-def]
    present = api_client.get("/api/v1/overview", params={"reference_date": REF}).json()
    past = api_client.get(
        "/api/v1/overview", params={"reference_date": "2026-01-01T00:00:00Z"}
    ).json()
    assert past["meta"]["reference_date"].startswith("2026-01-01")
    assert past["health"]["revenue"]["value"] >= 0
    assert past["trends"][0]["period_end"].startswith("2026-01-01")
    assert past["trends"] != present["trends"]


def test_overview_links_are_real(api_client: TestClient, ml_db: Session) -> None:  # type: ignore[no-untyped-def]
    from app.models.customer import Customer

    customer_ids = set(ml_db.scalars(select(Customer.id)).all())
    body = api_client.get("/api/v1/overview", params={"reference_date": REF}).json()
    for item in body["opportunities"]:
        assert item["customer_id"] in customer_ids
        hrefs = [link["href"] for link in item["links"]]
        assert f"/customers/{item['customer_id']}" in hrefs
    for item in body["attention"]:
        assert item["affected_customers"] <= body["meta"]["customer_count"]
        for link in item["links"]:
            assert link["kind"] in ("section", "entity")
            if link["kind"] == "section":
                assert link["href"] in KNOWN_SECTIONS
            else:
                assert link["href"].startswith("/customers/")
                assert int(link["href"].rsplit("/", 1)[-1]) in customer_ids


def test_overview_empty_database() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app()

    def override():  # type: ignore[no-untyped-def]
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "empty-owner@example.com", "password": "s3cure-pass"},
        ).status_code
        == 201
    )
    body = client.get("/api/v1/overview").json()
    assert body["meta"]["customer_count"] == 0
    assert body["health"]["revenue"]["value"] == 0.0
    assert body["health"]["revenue"]["change_pct"] is None
    assert all(bucket["revenue"] == 0 for bucket in body["trends"])
    assert body["attention"] == []
    assert body["opportunities"] == []
    app.dependency_overrides.clear()


def test_overview_degrades_without_models(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    response = overview_service.get_overview(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    assert response.meta.ml_available is False
    assert response.opportunities == []
    assert response.health.revenue.value >= 0


def test_overview_query_count_stays_flat(ml_db: Session, trained_dir) -> None:  # type: ignore[no-untyped-def]
    engine = ml_db.get_bind()
    calls: list[str] = []

    def counter(conn, cursor, statement, parameters, context, executemany) -> None:
        calls.append(str(statement)[:40])

    event.listen(engine, "before_cursor_execute", counter)
    try:
        overview_service.get_overview(ml_db, REF_DT, artifacts_dir=trained_dir)
    finally:
        event.remove(engine, "before_cursor_execute", counter)
    # Batch aggregates + one feature pass: must not scale with customer count.
    assert len(calls) < 40, f"{len(calls)} queries — possible N+1"
