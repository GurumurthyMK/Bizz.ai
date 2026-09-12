"""Lifecycle tests: missing artifacts, inference without retraining, contracts."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.ml import inference
from app.ml.churn import bundle_churn, train_churn
from app.ml.persistence import (
    ModelNotTrainedError,
    load_bundle,
    save_bundle,
)
from app.ml.preprocessing import FeatureMismatchError
from app.ml.purchase import bundle_purchase, train_purchase
from app.ml.segmentation import bundle_segmentation, train_segmentation

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


def _train_all(ml_db: Session, directory: Path) -> None:
    seg_model, seg_result = train_segmentation(ml_db, TRAIN_REF)
    save_bundle("segmentation", bundle_segmentation(seg_model, seg_result), directory)
    churn_model, churn_metrics = train_churn(ml_db, TRAIN_REF)
    save_bundle("churn", bundle_churn(churn_model, churn_metrics), directory)
    purchase_model, purchase_metrics = train_purchase(ml_db, TRAIN_REF)
    save_bundle("purchase", bundle_purchase(purchase_model, purchase_metrics), directory)


def test_inference_without_artifacts_raises(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import TestingSession

    db = TestingSession()
    try:
        with pytest.raises(ModelNotTrainedError):
            inference.predict_churn(db, TRAIN_REF, artifacts_dir=tmp_path)
        with pytest.raises(ModelNotTrainedError):
            inference.predict_segments(db, TRAIN_REF, artifacts_dir=tmp_path)
        with pytest.raises(ModelNotTrainedError):
            inference.predict_purchase(db, TRAIN_REF, artifacts_dir=tmp_path)
    finally:
        db.close()


def test_inference_services_cover_all_customers(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _train_all(ml_db, tmp_path)

    segments = inference.predict_segments(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    churn_scores = inference.predict_churn(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    purchase_scores = inference.predict_purchase(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    opportunities = inference.predict_opportunities(ml_db, TRAIN_REF, artifacts_dir=tmp_path)

    assert len(segments) == len(churn_scores) == len(purchase_scores) == len(opportunities) == 300
    assert all(set(item) == {"customer_id", "cluster_id", "business_label"} for item in segments)
    assert all(0.0 <= item["cluster_id"] <= 4 for item in segments)
    assert all(0.0 <= score.churn_probability <= 1.0 for score in churn_scores)
    assert all(0.0 <= score.purchase_probability <= 1.0 for score in purchase_scores)
    assert all(0.0 <= score.score <= 1.0 for score in opportunities)
    assert inference.predict_churn(ml_db, TRAIN_REF, customer_ids=[], artifacts_dir=tmp_path) == []


def test_inference_does_not_retrain_or_modify_artifacts(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _train_all(ml_db, tmp_path)
    before = {
        kind: (tmp_path / f"{kind}.joblib").stat().st_mtime_ns
        for kind in ("segmentation", "churn", "purchase")
    }
    inference.predict_segments(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    inference.predict_churn(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    inference.predict_purchase(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    inference.predict_opportunities(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
    after = {
        kind: (tmp_path / f"{kind}.joblib").stat().st_mtime_ns
        for kind in ("segmentation", "churn", "purchase")
    }
    assert before == after


def test_tampered_column_contract_is_rejected(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    _train_all(ml_db, tmp_path)
    bundle = load_bundle("churn", tmp_path)
    bundle["feature_names"] = bundle["feature_names"][:-1]
    save_bundle("churn", bundle, tmp_path)
    with pytest.raises(FeatureMismatchError):
        inference.predict_churn(ml_db, TRAIN_REF, artifacts_dir=tmp_path)
