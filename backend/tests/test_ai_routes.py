"""AI route tests: grounding, failures, validation, secret handling.

The provider dependency is overridden with fakes — no network, no keys.
The module database is seeded business data plus materialized intelligence,
mirroring production shape at small scale.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.routes.ai import get_llm_provider
from app.db.base import Base
from app.db.session import get_db
from app.llm.provider import (
    LLMError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
)
from app.main import create_app
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.segment import Segment

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


class FakeProvider(LLMProvider):
    """Records prompts; answers from canned text. No network."""

    name = "fake"

    def __init__(self) -> None:
        super().__init__(model="fake-1")
        self.prompts: list[str] = []
        self.systems: list[str | None] = []

    def generate(self, prompt: str, system=None, transport=None) -> LLMResponse:  # type: ignore[no-untyped-def]
        self.prompts.append(prompt)
        self.systems.append(system)
        return LLMResponse(
            text="Grounded explanation from verified context.", model="fake-1", provider="fake"
        )


class FailingProvider(LLMProvider):
    name = "failing"

    def __init__(self, error: Exception) -> None:
        super().__init__(model="failing-1")
        self._error = error

    def generate(self, prompt: str, system=None, transport=None) -> LLMResponse:  # type: ignore[no-untyped-def]
        raise self._error


@pytest.fixture(scope="module")
def ai_env(ml_db: Session):  # type: ignore[no-untyped-def]
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace

    from app.ml.churn import bundle_churn, train_churn
    from app.ml.persistence import save_bundle
    from app.ml.purchase import bundle_purchase, train_purchase
    from app.ml.segmentation import bundle_segmentation, train_segmentation
    from app.services.intelligence import materialize_intelligence

    tmp = Path(tempfile.mkdtemp(prefix="ai-artifacts-"))
    seg_model, seg_result = train_segmentation(ml_db, TRAIN_REF)
    save_bundle("segmentation", bundle_segmentation(seg_model, seg_result), tmp)
    churn_model, churn_metrics = train_churn(ml_db, TRAIN_REF)
    save_bundle("churn", bundle_churn(churn_model, churn_metrics), tmp)
    purchase_model, purchase_metrics = train_purchase(ml_db, TRAIN_REF)
    save_bundle("purchase", bundle_purchase(purchase_model, purchase_metrics), tmp)
    materialize_intelligence(ml_db, TRAIN_REF, artifacts_dir=tmp)

    engine = ml_db.get_bind()
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
        json={"email": "ai-owner@example.com", "password": "s3cure-pass"},
    )
    assert response.status_code == 201
    yield SimpleNamespace(app=app, client=client, fake=fake, factory=factory)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def ai_client(ai_env):  # type: ignore[no-untyped-def]
    yield ai_env.client, ai_env.fake


def test_insight_overview_grounded(ai_client, ml_db: Session) -> None:
    client, fake = ai_client
    body = client.post("/api/v1/ai/insight", json={"context": {"kind": "overview"}}).json()
    assert body["context_kind"] == "overview"
    assert body["provider"] == "fake"
    assert "Grounded explanation" in body["text"]
    prompt = fake.prompts[-1]
    assert "revenue" in prompt.lower()
    assert "Never invent" in fake.systems[-1]


def test_ask_includes_question(ai_client) -> None:
    client, fake = ai_client
    body = client.post(
        "/api/v1/ai/ask",
        json={"context": {"kind": "overview"}, "question": "Why did revenue change?"},
    ).json()
    assert body["context_kind"] == "overview"
    assert "Why did revenue change?" in fake.prompts[-1]


def test_summarize_customer_links_entity(ai_client, ml_db: Session) -> None:
    client, _ = ai_client
    customer_id = ml_db.scalars(select(Customer.id).limit(1)).one()
    body = client.post(
        "/api/v1/ai/summarize", json={"context": {"kind": "customer", "id": customer_id}}
    ).json()
    assert body["context_kind"] == "customer"


def test_insight_segment_and_opportunity(ai_client, ml_db: Session) -> None:
    client, fake = ai_client
    segment_id = ml_db.scalars(select(Segment.id).limit(1)).one()
    seg = client.post(
        "/api/v1/ai/insight", json={"context": {"kind": "segment", "id": segment_id}}
    ).json()
    assert seg["context_kind"] == "segment"
    opportunity_id = ml_db.scalars(select(Opportunity.id).limit(1)).one()
    opp = client.post(
        "/api/v1/ai/insight", json={"context": {"kind": "opportunity", "id": opportunity_id}}
    ).json()
    assert opp["context_kind"] == "opportunity"
    assert str(opportunity_id) in fake.prompts[-1]


def test_provider_failure_maps_to_503(ai_env) -> None:
    """A dead provider yields 503 with a safe message — and BI still works."""
    ai_env.app.dependency_overrides[get_llm_provider] = lambda: FailingProvider(
        LLMProviderError("boom")
    )
    try:
        # ai_env.client already holds a session cookie from registration.
        response = ai_env.client.post("/api/v1/ai/insight", json={"context": {"kind": "overview"}})
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()
        assert "boom" not in response.json()["detail"]
        assert ai_env.client.get("/api/v1/overview").status_code == 200
    finally:
        ai_env.app.dependency_overrides[get_llm_provider] = lambda: ai_env.fake


def test_disabled_provider_returns_503() -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from app.main import create_app

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app()

    def override_db():  # type: ignore[no-untyped-def]
        session = factory()
        try:
            yield session
        finally:
            session.close()

    def override_provider() -> LLMProvider:
        from app.llm.provider import DisabledProvider

        return DisabledProvider()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_llm_provider] = override_provider
    client = TestClient(app)
    client.post(
        "/api/v1/auth/register",
        json={"email": "ai-disabled@example.com", "password": "s3cure-pass"},
    )
    response = client.post("/api/v1/ai/insight", json={"context": {"kind": "overview"}})
    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"].lower()
    # BI itself keeps working without a provider.
    assert client.get("/api/v1/overview").status_code == 200
    app.dependency_overrides.clear()


def test_service_error_contract() -> None:
    """Service-level errors stay inside the LLMError hierarchy."""
    from app.llm.service import generate_insight

    with pytest.raises(LLMError):
        generate_insight(
            {"kind": "overview", "data": {}},
            provider=FailingProvider(LLMProviderError("boom")),
        )


def test_validation_errors(ai_client) -> None:
    client, _ = ai_client
    assert client.post("/api/v1/ai/insight", json={"context": {"kind": "bogus"}}).status_code == 422
    assert (
        client.post(
            "/api/v1/ai/insight", json={"context": {"kind": "overview", "id": 1}}
        ).status_code
        == 422
    )
    assert (
        client.post("/api/v1/ai/insight", json={"context": {"kind": "customer"}}).status_code == 422
    )
    assert (
        client.post(
            "/api/v1/ai/ask", json={"context": {"kind": "overview"}, "question": "  "}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/ai/ask",
            json={"context": {"kind": "overview"}, "question": "x" * 1001},
        ).status_code
        == 422
    )


def test_missing_entity_returns_404(ai_client) -> None:
    client, _ = ai_client
    response = client.post(
        "/api/v1/ai/insight", json={"context": {"kind": "customer", "id": 999999}}
    )
    assert response.status_code == 404


def test_ai_requires_authentication() -> None:
    from app.main import create_app

    client = TestClient(create_app())
    assert (
        client.post("/api/v1/ai/insight", json={"context": {"kind": "overview"}}).status_code == 401
    )
    assert (
        client.post(
            "/api/v1/ai/ask", json={"context": {"kind": "overview"}, "question": "Hi?"}
        ).status_code
        == 401
    )


def test_no_secrets_in_responses(ai_client) -> None:
    client, _ = ai_client
    for path, payload in [
        ("/api/v1/ai/insight", {"context": {"kind": "overview"}}),
        ("/api/v1/ai/ask", {"context": {"kind": "overview"}, "question": "Hi?"}),
        ("/api/v1/ai/summarize", {"context": {"kind": "overview"}}),
    ]:
        body = client.post(path, json=payload).json()
        assert set(body) == {"text", "model", "provider", "context_kind"}
        blob = str(body).lower()
        assert "sk-" not in blob and "api_key" not in blob and "api-key" not in blob


def test_overview_counts(ai_client, ml_db: Session) -> None:
    assert ml_db.scalar(select(func.count()).select_from(Segment)) == 5
