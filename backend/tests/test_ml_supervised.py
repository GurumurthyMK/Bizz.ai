"""Churn/purchase tests: labels, training, probabilities, signals, edges."""

from datetime import UTC, date, datetime

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.analytics.features import build_customer_features
from app.ml import churn as churn_module
from app.ml import purchase as purchase_module
from app.ml.labels import churn_labels, purchase_labels
from app.ml.preprocessing import FeatureMismatchError
from tests.analytics_helpers import add_customer, add_product, add_txn, at

TRAIN_REF = datetime(2026, 4, 1, tzinfo=UTC)


def _hand_built_db() -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.db.base import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_label_definitions() -> None:
    db = _hand_built_db()
    product = add_product(db, "lbl", tag="lbl")
    active = add_customer(db, "lbl", tag="stay")
    churned = add_customer(db, "lbl", tag="leave")
    ghost = add_customer(db, "lbl", tag="ghost")
    add_txn(db, active.id, product.id, at(date(2026, 1, 10)), unit_price=10.0)
    add_txn(db, active.id, product.id, at(date(2026, 4, 10)), unit_price=10.0)
    add_txn(db, churned.id, product.id, at(date(2026, 1, 10)), unit_price=10.0)
    db.commit()

    ref = datetime(2026, 3, 1, tzinfo=UTC)
    churn = churn_labels(db, ref, 90, [active.id, churned.id, ghost.id])
    assert churn[active.id] == 0
    assert churn[churned.id] == 1
    assert ghost.id not in churn  # never active: ineligible, not assumed retained

    purchase = purchase_labels(db, ref, 30, [active.id, churned.id, ghost.id])
    assert purchase[active.id] == 0  # Apr 10 is outside the 30-day window
    assert purchase[churned.id] == 0
    assert purchase[ghost.id] == 0
    purchase_wide = purchase_labels(db, ref, 60, [active.id])
    assert purchase_wide[active.id] == 1
    db.close()


def test_churn_train_evaluate_deterministic(ml_db: Session) -> None:
    _, first = churn_module.train_churn(ml_db, TRAIN_REF)
    _, second = churn_module.train_churn(ml_db, TRAIN_REF)
    assert first.model_dump() == second.model_dump()
    assert 0.0 <= first.precision <= 1.0
    assert 0.0 <= first.recall <= 1.0
    assert 0.0 <= first.f1 <= 1.0
    assert first.roc_auc is None or 0.0 <= first.roc_auc <= 1.0
    assert first.n_train > 0 and first.n_test > 0


def test_purchase_train_evaluate_deterministic(ml_db: Session) -> None:
    _, first = purchase_module.train_purchase(ml_db, TRAIN_REF)
    _, second = purchase_module.train_purchase(ml_db, TRAIN_REF)
    assert first.model_dump() == second.model_dump()
    assert 0.0 <= first.f1 <= 1.0


def test_probability_ranges_and_signals(ml_db: Session) -> None:
    churn_model, _ = churn_module.train_churn(ml_db, TRAIN_REF)
    purchase_model, _ = purchase_module.train_purchase(ml_db, TRAIN_REF)
    records = build_customer_features(ml_db, TRAIN_REF)[:10]

    churn_scores = churn_model.score_customers(records)
    purchase_scores = purchase_model.score_customers(records)
    for score in churn_scores:
        assert 0.0 <= score.churn_probability <= 1.0
        assert score.risk_band in ("low", "medium", "high")
        assert score.signals and all(isinstance(text, str) for text in score.signals)
    for score in purchase_scores:
        assert 0.0 <= score.purchase_probability <= 1.0
        assert score.likelihood_band in ("low", "medium", "high")
        assert score.signals


def test_single_class_training_raises() -> None:
    db = _hand_built_db()
    product = add_product(db, "one", tag="one")
    for tag in ("a", "b", "c", "d", "e"):
        customer = add_customer(db, "one", tag=f"one-{tag}")
        add_txn(db, customer.id, product.id, at(date(2026, 1, 5)), unit_price=10.0)
    db.commit()
    ref = datetime(2026, 3, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        churn_module.train_churn(db, ref)
    db.close()


def test_model_persistence_roundtrip(ml_db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.ml.persistence import load_bundle, save_bundle

    churn_model, metrics = churn_module.train_churn(ml_db, TRAIN_REF)
    save_bundle("churn", churn_module.bundle_churn(churn_model, metrics), tmp_path)
    restored = churn_module.load_churn(load_bundle("churn", tmp_path))

    records = build_customer_features(ml_db, TRAIN_REF)[:5]
    original = [score.churn_probability for score in churn_model.score_customers(records)]
    reloaded = [score.churn_probability for score in restored.score_customers(records)]
    assert original == reloaded


def test_feature_mismatch_raises(ml_db: Session) -> None:
    churn_model, _ = churn_module.train_churn(ml_db, TRAIN_REF)
    with pytest.raises(FeatureMismatchError):
        churn_model.predict_proba(np.zeros((2, 5)))
