"""Churn prediction: supervised churn-risk model with explainable signals.

Target (see ``app.ml.labels``): 1 when a previously-active customer places
zero completed orders in the 90 days after the reference date. Training uses
a historical reference date so labels are observed, never leaked.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression
from sqlalchemy.orm import Session

from app.analytics.features import CustomerFeatures, build_customer_features
from app.ml.labels import CHURN_HORIZON_DAYS, churn_labels
from app.ml.preprocessing import (
    MODEL_FEATURES,
    FeatureMismatchError,
    FeaturePreprocessor,
    vectors_from_records,
)
from app.ml.supervised import (
    ClassificationMetrics,
    evaluate_classifier,
    new_classifier,
    split_dataset,
    top_signals,
)


class ChurnScore(BaseModel):
    customer_id: int
    churn_probability: float
    risk_band: str
    signals: list[str]


def risk_band(probability: float) -> str:
    if probability >= 2 / 3:
        return "high"
    if probability >= 1 / 3:
        return "medium"
    return "low"


class ChurnModel:
    """Balanced logistic regression; inference never retrains."""

    def __init__(self) -> None:
        self.preprocessor = FeaturePreprocessor(MODEL_FEATURES)
        self.classifier: LogisticRegression = new_classifier()
        self._fitted = False

    def fit(self, matrix: np.ndarray, labels: np.ndarray) -> ChurnModel:
        classes = set(np.asarray(labels).tolist())
        if len(classes) < 2:
            raise ValueError("churn training needs both churned and retained customers")
        if min(int((labels == cls).sum()) for cls in classes) < 2:
            raise ValueError("churn training needs at least 2 samples per class")
        scaled = self.preprocessor.fit_transform(matrix)
        self.classifier.fit(scaled, labels)
        self._fitted = True
        return self

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("ChurnModel is not fitted")

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        self._require_fitted()
        if np.asarray(matrix).shape[1] != self.preprocessor.n_features:
            raise FeatureMismatchError(
                f"churn model expects {self.preprocessor.n_features} columns"
            )
        return self.classifier.predict_proba(self.preprocessor.transform(matrix))[:, 1]

    def score_customers(self, records: list[CustomerFeatures]) -> list[ChurnScore]:
        self._require_fitted()
        matrix, ids = vectors_from_records(records, MODEL_FEATURES)
        standardized = self.preprocessor.transform(matrix)
        probabilities = self.classifier.predict_proba(standardized)[:, 1]
        coefficients = np.asarray(self.classifier.coef_[0])
        scores = []
        for position, customer_id in enumerate(ids):
            probability = float(probabilities[position])
            signals = top_signals(
                coefficients,
                MODEL_FEATURES,
                standardized[position],
                matrix[position],
                k=3,
                empty_message="no elevated churn signals",
            )
            scores.append(
                ChurnScore(
                    customer_id=customer_id,
                    churn_probability=probability,
                    risk_band=risk_band(probability),
                    signals=signals,
                )
            )
        return scores


def train_churn(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    horizon_days: int = CHURN_HORIZON_DAYS,
) -> tuple[ChurnModel, ClassificationMetrics]:
    """Train on features as of ``reference_date`` with observed churn labels."""
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    labels_by_customer = churn_labels(db, reference_date, horizon_days, customer_ids)
    eligible = [record for record in records if record.customer_id in labels_by_customer]
    if not eligible:
        raise ValueError("no eligible customers for churn training")
    matrix, _ = vectors_from_records(eligible, MODEL_FEATURES)
    labels = np.array([labels_by_customer[record.customer_id] for record in eligible])
    X_train, X_test, y_train, y_test = split_dataset(matrix, labels)
    model = ChurnModel().fit(X_train, y_train)
    scaled_test = model.preprocessor.transform(X_test)
    metrics = evaluate_classifier(model.classifier, scaled_test, y_test, len(y_train))
    return model, metrics


def bundle_churn(model: ChurnModel, metrics: ClassificationMetrics) -> dict:
    return {
        "kind": "churn",
        "feature_names": model.preprocessor.feature_names,
        "scaler": model.preprocessor.scaler,
        "classifier": model.classifier,
        "metrics": metrics.model_dump(),
        "horizon_days": CHURN_HORIZON_DAYS,
    }


def load_churn(bundle: dict) -> ChurnModel:
    model = ChurnModel()
    model.preprocessor = FeaturePreprocessor(list(bundle["feature_names"]))
    model.preprocessor.scaler = bundle["scaler"]
    model.classifier = bundle["classifier"]
    model._fitted = True
    return model
