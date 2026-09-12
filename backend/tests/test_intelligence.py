"""Intelligence tests: materialization, relationships, workflows, API.

Runs against the isolated seeded ``ml_db`` database with tiny models trained
into a temporary artifacts directory — real ML outputs, small scale.
"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.models.segment import Segment
from app.services.intelligence import (
    CHURN_MODEL_VERSION,
    OPPORTUNITY_MODEL_VERSION,
    PURCHASE_MODEL_VERSION,
    SEGMENT_MODEL_VERSION,
    get_intelligence_status,
    materialize_intelligence,
)

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def materialized(ml_db: Session, tmp_path_factory):  # type: ignore[no-untyped-def]
    from app.ml.churn import bundle_churn, train_churn
    from app.ml.persistence import save_bundle
    from app.ml.purchase import bundle_purchase, train_purchase
    from app.ml.segmentation import bundle_segmentation, train_segmentation

    directory = tmp_path_factory.mktemp("intel-artifacts-full")
    seg_model, seg_result = train_segmentation(ml_db, TRAIN_REF)
    save_bundle("segmentation", bundle_segmentation(seg_model, seg_result), directory)
    churn_model, churn_metrics = train_churn(ml_db, TRAIN_REF)
    save_bundle("churn", bundle_churn(churn_model, churn_metrics), directory)
    purchase_model, purchase_metrics = train_purchase(ml_db, TRAIN_REF)
    save_bundle("purchase", bundle_purchase(purchase_model, purchase_metrics), directory)
    report = materialize_intelligence(ml_db, TRAIN_REF, artifacts_dir=directory)
    return report, directory


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
        json={"email": "intel-owner@example.com", "password": "s3cure-pass"},
    )
    assert response.status_code == 201
    yield client
    app.dependency_overrides.clear()


def test_materialize_counts(materialized, ml_db: Session) -> None:
    report, _ = materialized
    assert report.segments == 5
    assert report.predictions == 600
    assert report.opportunities > 0
    assert report.customers_linked == 300
    assert ml_db.scalar(select(func.count()).select_from(Segment)) == 5
    assert ml_db.scalar(select(func.count()).select_from(Prediction)) == 600


def test_materialize_is_idempotent(ml_db: Session, materialized) -> None:
    _, directory = materialized
    again = materialize_intelligence(ml_db, TRAIN_REF, artifacts_dir=directory)
    assert again.segments == 5
    assert again.predictions == 600
    assert ml_db.scalar(select(func.count()).select_from(Segment)) == 5
    assert ml_db.scalar(select(func.count()).select_from(Prediction)) == 600
    assert ml_db.scalar(select(func.count()).select_from(Opportunity)) == again.opportunities


def test_relationships_cover_all_customers(ml_db: Session, materialized) -> None:
    customers = ml_db.scalars(select(Customer)).all()
    assert all(customer.segment_id is not None for customer in customers)
    member_total = sum(len(segment.customers) for segment in ml_db.scalars(select(Segment)).all())
    assert member_total == 300
    prediction = ml_db.scalars(select(Prediction).limit(1)).one()
    assert prediction.customer is not None
    opportunity = ml_db.scalars(select(Opportunity).limit(1)).one()
    assert opportunity.customer is not None
    assert opportunity.segment_id == opportunity.customer.segment_id
    assert opportunity.recommended_action
    assert opportunity.estimated_value >= 0


def test_persisted_versions_and_reference(ml_db: Session, materialized) -> None:
    segment = ml_db.scalars(select(Segment).limit(1)).one()
    assert segment.model_version == SEGMENT_MODEL_VERSION
    churn = ml_db.scalars(
        select(Prediction).where(Prediction.prediction_type == "churn").limit(1)
    ).one()
    assert churn.model_version == CHURN_MODEL_VERSION
    purchase = ml_db.scalars(
        select(Prediction).where(Prediction.prediction_type == "purchase").limit(1)
    ).one()
    assert purchase.model_version == PURCHASE_MODEL_VERSION
    opportunity = ml_db.scalars(select(Opportunity).limit(1)).one()
    assert opportunity.model_version == OPPORTUNITY_MODEL_VERSION
    assert opportunity.reference_date is not None


def test_persisted_probabilities_match_model_output(ml_db: Session, materialized) -> None:
    from app.ml.inference import predict_churn

    _, directory = materialized
    customer_id = ml_db.scalars(select(Customer.id).limit(1)).one()
    live = predict_churn(ml_db, TRAIN_REF, customer_ids=[customer_id], artifacts_dir=directory)
    stored = ml_db.scalars(
        select(Prediction).where(
            Prediction.customer_id == customer_id,
            Prediction.prediction_type == "churn",
        )
    ).one()
    assert stored.probability == pytest.approx(live[0].churn_probability)
    assert stored.band == live[0].risk_band
    assert stored.signal_list() == live[0].signals


def test_segments_api(api_client: TestClient, materialized, ml_db: Session) -> None:
    body = api_client.get("/api/v1/segments").json()
    assert len(body) == 5
    assert all({"id", "name", "size", "share"} <= set(item) for item in body)
    assert sum(item["size"] for item in body) == 300

    segment_id = body[0]["id"]
    detail = api_client.get(f"/api/v1/segments/{segment_id}").json()
    assert detail["name"] == body[0]["name"]

    members = api_client.get(
        f"/api/v1/segments/{segment_id}/customers", params={"page_size": 10}
    ).json()
    assert members["total"] == body[0]["size"]
    assert len(members["items"]) == min(10, body[0]["size"])

    assert api_client.get("/api/v1/segments/999999").status_code == 404


def test_predictions_api(api_client: TestClient, materialized, ml_db: Session) -> None:
    churn_only = api_client.get("/api/v1/predictions", params={"prediction_type": "churn"}).json()
    assert churn_only["total"] == 300
    assert all(item["prediction_type"] == "churn" for item in churn_only["items"])

    high = api_client.get("/api/v1/predictions", params={"band": "high"}).json()
    assert all(item["band"] == "high" for item in high["items"])

    asc = api_client.get(
        "/api/v1/predictions",
        params={
            "prediction_type": "purchase",
            "sort_by": "probability",
            "order": "asc",
            "page_size": 5,
        },
    ).json()
    probabilities = [item["probability"] for item in asc["items"]]
    assert probabilities == sorted(probabilities)

    customer_id = ml_db.scalars(select(Customer.id).limit(1)).one()
    mine = api_client.get("/api/v1/predictions", params={"customer_id": customer_id}).json()
    assert mine["total"] == 2
    assert {item["prediction_type"] for item in mine["items"]} == {"churn", "purchase"}

    first_id = churn_only["items"][0]["id"]
    detail = api_client.get(f"/api/v1/predictions/{first_id}").json()
    assert detail["signals"] is not None
    assert api_client.get("/api/v1/predictions/999999").status_code == 404


def test_opportunities_api(api_client: TestClient, materialized, ml_db: Session) -> None:
    body = api_client.get("/api/v1/opportunities", params={"page_size": 5}).json()
    assert body["total"] > 0
    scores = [item["score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert all(item["score"] >= 0.4 for item in body["items"])

    high = api_client.get("/api/v1/opportunities", params={"tier": "high"}).json()
    assert all(item["tier"] == "high" for item in high["items"])

    first = body["items"][0]
    assert first["reasons"] and first["recommended_action"] and first["opportunity_type"]
    detail = api_client.get(f"/api/v1/opportunities/{first['id']}").json()
    assert detail["customer_id"] == first["customer_id"]
    assert api_client.get("/api/v1/opportunities/999999").status_code == 404

    by_segment = api_client.get(
        "/api/v1/opportunities", params={"segment_id": first["segment_id"]}
    ).json()
    assert all(item["segment_id"] == first["segment_id"] for item in by_segment["items"])


def test_customer_intelligence_api(api_client: TestClient, materialized, ml_db: Session) -> None:
    customer_id = ml_db.scalars(select(Customer.id).limit(1)).one()
    body = api_client.get(f"/api/v1/customers/{customer_id}/intelligence").json()
    assert body["customer"]["id"] == customer_id
    assert body["metrics"]["customer_id"] == customer_id
    assert body["segment"] is not None
    assert body["segment"]["id"] is not None
    assert len(body["predictions"]) == 2
    assert {item["prediction_type"] for item in body["predictions"]} == {"churn", "purchase"}
    assert all(item["customer_id"] == customer_id for item in body["opportunities"])
    assert api_client.get("/api/v1/customers/999999/intelligence").status_code == 404


def test_intelligence_status_and_auth(api_client: TestClient, materialized) -> None:
    body = api_client.get("/api/v1/intelligence/status").json()
    assert body["materialized"] is True
    assert body["segments"] == 5
    assert body["predictions"] == 600
    assert body["customers_linked"] == 300
    assert body["reference_date"] is not None

    fresh = TestClient(create_app())
    assert fresh.get("/api/v1/segments").status_code == 401
    assert fresh.get("/api/v1/predictions").status_code == 401
    assert fresh.get("/api/v1/opportunities").status_code == 401
    assert fresh.get("/api/v1/intelligence/status").status_code == 401
    assert fresh.post("/api/v1/intelligence/materialize").status_code == 401


def test_materialize_requires_artifacts(tmp_path) -> None:
    """Missing artifacts fail loudly — output is never faked."""
    from app.ml.persistence import ModelNotTrainedError

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        with pytest.raises(ModelNotTrainedError):
            materialize_intelligence(db, TRAIN_REF, artifacts_dir=tmp_path)
        status = get_intelligence_status(db)
        assert status.materialized is False
        assert status.reference_date is None
    finally:
        db.close()


def test_materialize_empty_database(materialized) -> None:
    """Artifacts present but no customers: empty report, empty tables, no crash."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        _, directory = materialized
        report = materialize_intelligence(db, TRAIN_REF, artifacts_dir=directory)
        assert report.segments == 0
        assert report.predictions == 0
        assert report.opportunities == 0
        assert report.customers_linked == 0
        assert get_intelligence_status(db).materialized is False
    finally:
        db.close()
