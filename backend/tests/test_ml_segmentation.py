"""Segmentation tests: determinism, summaries, labels, persistence, edges."""

from datetime import UTC, datetime

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.ml.preprocessing import SEGMENT_FEATURES, FeatureMismatchError
from app.ml.segmentation import (
    BUSINESS_LABELS,
    N_CLUSTERS,
    SegmentationModel,
    bundle_segmentation,
    label_cluster,
    load_segmentation,
    train_segmentation,
)

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


def test_label_cluster_partitions_the_space() -> None:
    seen: set[str] = set()
    for recency in (0, 30, 45, 60, 120, 181, 400):
        for orders in (0, 1, 3, 5, 20):
            for revenue in (0, 500, 5000):
                label = label_cluster(recency, orders, 5.0, 1000.0, revenue)
                assert label in BUSINESS_LABELS
                seen.add(label)
    assert {"Champions", "Lost", "New Customers", "At Risk"} <= seen


def test_train_segmentation_deterministic(ml_db: Session) -> None:
    _, first = train_segmentation(ml_db, TRAIN_REF)
    _, second = train_segmentation(ml_db, TRAIN_REF)
    assert first.silhouette == pytest.approx(second.silhouette)
    assert first.inertia == pytest.approx(second.inertia)
    assert first.assignments == second.assignments
    assert first.n_clusters == N_CLUSTERS


def test_segmentation_summaries_and_metrics(ml_db: Session) -> None:
    _, result = train_segmentation(ml_db, TRAIN_REF)
    assert len(result.summaries) == N_CLUSTERS
    assert sum(summary.size for summary in result.summaries) == 300
    assert sum(summary.share for summary in result.summaries) == pytest.approx(1.0)
    assert all(summary.business_label in BUSINESS_LABELS for summary in result.summaries)
    assert result.silhouette is not None
    assert -1.0 <= result.silhouette <= 1.0
    assert set(result.assignments.values()) == set(range(N_CLUSTERS))


def test_segmentation_persistence_roundtrip(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.ml.persistence import load_bundle, save_bundle

    model, result = train_segmentation(ml_db, TRAIN_REF)
    path = save_bundle("segmentation", bundle_segmentation(model, result), tmp_path)
    assert path.exists()
    restored = load_segmentation(load_bundle("segmentation", tmp_path))

    from app.analytics.features import build_customer_features
    from app.ml.preprocessing import vectors_from_records

    records = build_customer_features(ml_db, TRAIN_REF)
    matrix, _ = vectors_from_records(records, SEGMENT_FEATURES)
    assert (model.predict(matrix) == restored.predict(matrix)).all()


def test_segmentation_empty_and_mismatch(ml_db: Session) -> None:
    with pytest.raises(ValueError):
        train_segmentation(ml_db, TRAIN_REF, customer_ids=[])
    model, _ = train_segmentation(ml_db, TRAIN_REF)
    with pytest.raises(FeatureMismatchError):
        model.predict(np.zeros((2, 3)))
    fresh = SegmentationModel()
    with pytest.raises(ValueError):
        fresh.predict(np.zeros((10, len(SEGMENT_FEATURES))))
