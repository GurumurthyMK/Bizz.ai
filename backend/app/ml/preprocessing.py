"""Feature preprocessing for ML: fixed column contract plus scaling.

All models consume vectors in ``FEATURE_NAMES`` order. The preprocessor
records the expected column count at fit time and refuses to transform
anything else, so a stale artifact can never silently score wrong features.
Non-finite values are mapped to 0.0 defensively (the feature layer already
guarantees finite output).
"""

from __future__ import annotations

import numpy as np
from sklearn.preprocessing import StandardScaler

from app.analytics.features import FEATURE_NAMES, CustomerFeatures

MODEL_FEATURES: list[str] = list(FEATURE_NAMES)

# Compact, interpretable subset for clustering (RFM core + activity signals).
SEGMENT_FEATURES: list[str] = [
    "recency_days",
    "completed_orders",
    "total_revenue",
    "avg_order_value",
    "orders_last_90d",
    "total_interactions",
    "days_since_last_interaction",
    "order_trend_90d",
    "distinct_categories",
    "active_span_days",
]

assert set(SEGMENT_FEATURES) <= set(FEATURE_NAMES), "segment features must be a subset"


class FeatureMismatchError(Exception):
    """Raised when vectors do not match the fitted column contract."""


def vectors_from_records(
    records: list[CustomerFeatures], names: list[str] | None = None
) -> tuple[np.ndarray, list[int]]:
    """Stack record vectors (in ``names`` order) into a float matrix."""
    names = names or MODEL_FEATURES
    matrix = np.array(
        [[float(record.model_dump()[name]) for name in names] for record in records],
        dtype=float,
    )
    return matrix, [record.customer_id for record in records]


class FeaturePreprocessor:
    """Standard scaling with a frozen column contract."""

    def __init__(self, feature_names: list[str] | None = None) -> None:
        self.feature_names = list(feature_names or MODEL_FEATURES)
        self.scaler = StandardScaler()

    @property
    def n_features(self) -> int:
        return len(self.feature_names)

    def _check(self, matrix: np.ndarray) -> np.ndarray:
        cleaned = np.nan_to_num(np.asarray(matrix, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
        if cleaned.ndim != 2 or cleaned.shape[1] != self.n_features:
            raise FeatureMismatchError(
                f"expected {self.n_features} columns "
                f"({', '.join(self.feature_names[:3])}, ...), "
                f"got shape {cleaned.shape}"
            )
        return cleaned

    def fit(self, matrix: np.ndarray) -> FeaturePreprocessor:
        self.scaler.fit(self._check(matrix))
        return self

    def transform(self, matrix: np.ndarray) -> np.ndarray:
        return self.scaler.transform(self._check(matrix))

    def fit_transform(self, matrix: np.ndarray) -> np.ndarray:
        return self.scaler.fit_transform(self._check(matrix))

    def inverse_transform(self, matrix: np.ndarray) -> np.ndarray:
        return self.scaler.inverse_transform(np.asarray(matrix, dtype=float))
