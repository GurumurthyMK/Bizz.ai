"""Alert/report tests: conditions, dedup, evidence, fallback, authorization.

Hand-built fixture data on an isolated SQLite database keeps every condition
deterministic: exact thresholds, exact reference dates, exact expectations.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.ai import get_llm_provider
from app.db.base import Base
from app.db.session import get_db
from app.llm.provider import LLMProvider, LLMResponse
from app.main import create_app
from app.models.alert import Alert
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.models.product import Product
from app.models.segment import Segment
from app.models.transaction import Transaction
from app.services import alerts as alert_service
from app.services import reports as report_service

REF = datetime(2026, 9, 1, tzinfo=UTC)


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self) -> None:
        super().__init__(model="fake-1")
        self.prompts: list[str] = []

    def generate(self, prompt: str, system=None, transport=None) -> LLMResponse:  # type: ignore[no-untyped-def]
        self.prompts.append(prompt)
        return LLMResponse(text="Narrative from verified facts.", model="fake-1", provider="fake")


def _txn(db: Session, customer_id: int, product_id: int, when: datetime, total: float) -> None:
    db.add(
        Transaction(
            customer_id=customer_id,
            product_id=product_id,
            quantity=1,
            unit_price=total,
            discount=0,
            total_amount=total,
            status="completed",
            transaction_date=when,
        )
    )


@pytest.fixture(scope="module")
def alert_db():  # type: ignore[no-untyped-def]
    """Isolated database with conditions tuned to fire every alert type."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()

    active = Customer(first_name="Active", last_name="A", email="active@example.com")
    dormant = Customer(first_name="Dormant", last_name="D", email="dormant@example.com")
    db.add_all([active, dormant])
    db.flush()
    product = Product(sku="WIDGET", name="Widget", category="Tools", unit_price=100)
    db.add(product)
    db.flush()

    # Revenue + engagement only in the prior window: trailing window is empty,
    # so both decline conditions fire deterministically.
    prior_day = REF - timedelta(days=45)
    for _ in range(4):
        _txn(db, active.id, product.id, prior_day, 250.0)
    from app.models.interaction import Interaction

    db.add(
        Interaction(
            customer_id=active.id,
            interaction_type="open",
            channel="email",
            occurred_at=prior_day,
        )
    )
    db.add(
        Prediction(
            customer_id=dormant.id,
            prediction_type="churn",
            probability=0.9,
            band="high",
            signals=["no orders for 200 days"],
            model_version="test",
            reference_date=REF,
        )
    )
    db.add(
        Prediction(
            customer_id=active.id,
            prediction_type="purchase",
            probability=0.8,
            band="high",
            signals=["recent order"],
            model_version="test",
            reference_date=REF,
        )
    )
    segment = Segment(
        cluster_id=0,
        name="Testers",
        size=2,
        share=1.0,
        avg_recency_days=100.0,
        avg_completed_orders=2.0,
        avg_revenue=500.0,
        model_version="test",
        reference_date=REF,
    )
    db.add(segment)
    db.flush()
    active.segment_id = segment.id
    dormant.segment_id = segment.id
    db.add(
        Opportunity(
            customer_id=active.id,
            segment_id=segment.id,
            opportunity_type="purchase",
            score=0.85,
            tier="high",
            estimated_value=1000,
            reasons=["likely to buy"],
            signals={"purchase": 0.8},
            recommended_action="Send an offer.",
            model_version="test",
            reference_date=REF,
        )
    )
    db.commit()
    yield db
    db.close()


@pytest.fixture(scope="module")
def alert_client(alert_db: Session):  # type: ignore[no-untyped-def]
    engine = alert_db.get_bind()
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app()
    fake = FakeProvider()

    def override_db():  # type: ignore[no-untyped-def]
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_llm_provider] = lambda: fake
    client = TestClient(app)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "alerts-owner@example.com", "password": "s3cure-pass"},
    )
    assert response.status_code == 201
    yield client, fake
    app.dependency_overrides.clear()


def test_each_condition_fires_with_evidence(alert_db: Session) -> None:
    import app.services.alerts as alerts_module

    alerts_module.SEGMENT_MIN_SIZE = 2
    try:
        report = alert_service.materialize_alerts(alert_db, REF)
    finally:
        alerts_module.SEGMENT_MIN_SIZE = 50
    assert report["created"] == 5
    by_type = {}
    for alert in alert_db.scalars(select(Alert)).all():
        by_type.setdefault(alert.alert_type, []).append(alert)

    assert set(by_type) == {
        "high_churn_risk",
        "revenue_anomaly",
        "engagement_decline",
        "new_opportunity",
        "segment_change",
    }
    churn = by_type["high_churn_risk"][0]
    assert churn.severity == "high"
    assert churn.entity_type == "customer"
    assert churn.evidence["churn_probability"] == 0.9
    revenue = by_type["revenue_anomaly"][0]
    assert revenue.severity == "high"
    assert revenue.evidence["change_pct"] == -100.0
    assert revenue.entity_type == "metric"
    engagement = by_type["engagement_decline"][0]
    assert engagement.severity == "medium"
    opportunity = by_type["new_opportunity"][0]
    assert opportunity.entity_type == "opportunity"
    assert opportunity.evidence["score"] == 0.85
    segment = by_type["segment_change"][0]
    assert segment.entity_type == "segment"
    assert segment.evidence["risk_share"] == 0.5


def test_detection_avoids_duplicates(alert_db: Session) -> None:
    import app.services.alerts as alerts_module

    alerts_module.SEGMENT_MIN_SIZE = 2
    try:
        before = alert_db.scalar(select(func.count()).select_from(Alert))
        first = alert_service.materialize_alerts(alert_db, REF)
        second = alert_service.materialize_alerts(alert_db, REF)
    finally:
        alerts_module.SEGMENT_MIN_SIZE = 50
    assert second["created"] == 0
    assert second["skipped_duplicates"] == second["evaluated"]
    total = alert_db.scalar(select(func.count()).select_from(Alert))
    assert total == before + first["created"]
    assert first["created"] + first["skipped_duplicates"] == first["evaluated"]


def test_alerts_api_filters_acknowledge_and_auth(alert_client) -> None:
    client, _ = alert_client
    body = client.get("/api/v1/alerts").json()
    assert body["total"] == 5

    high = client.get("/api/v1/alerts", params={"severity": "high"}).json()
    assert high["total"] == 3
    assert all(item["severity"] == "high" for item in high["items"])

    churn = client.get("/api/v1/alerts", params={"alert_type": "high_churn_risk"}).json()
    assert churn["total"] == 1

    first_id = body["items"][0]["id"]
    detail = client.get(f"/api/v1/alerts/{first_id}").json()
    assert detail["evidence"] is not None
    assert client.get("/api/v1/alerts/999999").status_code == 404

    acked = client.patch(f"/api/v1/alerts/{first_id}/acknowledge").json()
    assert acked["status"] == "acknowledged"
    assert acked["acknowledged_at"] is not None
    active = client.get("/api/v1/alerts", params={"status": "active"}).json()
    assert active["total"] == 4

    fresh = TestClient(create_app())
    assert fresh.get("/api/v1/alerts").status_code == 401
    assert fresh.post("/api/v1/alerts/detect").status_code == 401
    assert fresh.post("/api/v1/reports/generate").status_code == 401


def test_detect_endpoint_returns_report(alert_client) -> None:
    client, _ = alert_client
    body = client.post("/api/v1/alerts/detect", params={"reference_date": REF.isoformat()}).json()
    # 4, not 5: the segment gate needs 50 members; the fixture has 2
    # (segment coverage is asserted at service level).
    assert body["evaluated"] == 4
    assert body["created"] == 0  # all already materialized: dedup holds via API too
    assert body["skipped_duplicates"] == 4


def test_report_sections_use_real_data(alert_client) -> None:
    client, _ = alert_client
    body = client.post(
        "/api/v1/reports/generate", params={"reference_date": REF.isoformat()}
    ).json()

    assert body["meta"]["llm_available"] is True
    assert "trailing 30 days" in body["executive_summary"]
    assert body["key_metrics"]["revenue"]["value"] == 0.0  # trailing window is empty
    assert body["key_metrics"]["transactions"]["previous_value"] == 4
    assert len(body["customer_trends"]) == 6
    assert body["segments"][0]["name"] == "Testers"
    assert body["predictions"]["churn_high_count"] == 1
    assert body["predictions"]["purchase_high_count"] == 1
    assert body["opportunities"]["total"] == 1
    assert body["opportunities"]["high_count"] == 1
    top_opp = body["opportunities"]["top"][0]
    assert top_opp["score"] == 0.85
    assert top_opp["recommended_action"] == "Send an offer."
    assert len(body["recommendations"]) > 0
    assert any("Retain 1 high-risk" in item["title"] for item in body["recommendations"])
    assert body["narrative"]["executive_summary"] == "Narrative from verified facts."
    assert body["narrative"]["model"] == "fake-1"


def test_report_llm_fallback_keeps_facts(alert_db: Session) -> None:
    from app.llm.provider import DisabledProvider

    # Explicitly disabled: narrative degrades regardless of ambient env config.
    report = report_service.generate_report(alert_db, REF, llm_provider=DisabledProvider())
    assert report.meta.llm_available is False
    assert report.narrative.executive_summary is None
    assert report.narrative.recommendations is None
    assert report.key_metrics.transactions.previous_value == 4
    assert report.predictions.churn_high_count == 1
    assert len(report.recommendations) > 0


def test_report_failing_llm_still_returns_facts(alert_db: Session) -> None:
    from app.llm.provider import LLMProviderError
    from tests.test_ai_routes import FailingProvider

    report = report_service.generate_report(
        alert_db, REF, llm_provider=FailingProvider(LLMProviderError("down"))
    )
    assert report.meta.llm_available is False
    assert report.narrative.executive_summary is None
    assert report.opportunities.total == 1
