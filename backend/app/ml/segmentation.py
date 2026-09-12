"""Customer segmentation: deterministic K-Means over interpretable features.

Configuration is frozen (``N_CLUSTERS``, ``RANDOM_STATE``, ``N_INIT``) so
retraining on the same data yields identical clusters. Cluster summaries
report size plus mean recency/orders/revenue in original units, and
``label_cluster`` maps those means to business names with ordered rules
that fully partition the space.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
from pydantic import BaseModel
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy.orm import Session

from app.analytics.features import build_customer_features
from app.ml.preprocessing import (
    SEGMENT_FEATURES,
    FeatureMismatchError,
    FeaturePreprocessor,
    vectors_from_records,
)

N_CLUSTERS = 5
RANDOM_STATE = 42
N_INIT = 10

BUSINESS_LABELS: tuple[str, ...] = (
    "Champions",
    "Loyal",
    "Growth Potential",
    "New Customers",
    "Occasional Buyers",
    "At Risk",
    "Lost",
)


class ClusterSummary(BaseModel):
    cluster_id: int
    size: int
    share: float
    avg_recency_days: float
    avg_completed_orders: float
    avg_revenue: float
    business_label: str


class SegmentationResult(BaseModel):
    n_clusters: int
    silhouette: float | None
    inertia: float
    summaries: list[ClusterSummary]
    assignments: dict[int, int]


def label_cluster(
    avg_recency: float, avg_orders: float, med_orders: float, med_revenue: float, avg_revenue: float
) -> str:
    """Ordered business rules; every (recency, orders, revenue) maps to one label."""
    if avg_recency <= 45 and avg_orders >= med_orders and avg_revenue >= med_revenue:
        return "Champions"
    if avg_recency <= 60 and avg_orders >= med_orders:
        return "Loyal"
    if avg_recency <= 45 and avg_orders <= 3:
        return "New Customers"
    if avg_recency <= 60:
        return "Growth Potential"
    if avg_recency > 180 and avg_orders < med_orders:
        return "Lost"
    if avg_recency > 180:
        return "At Risk"
    if avg_orders < med_orders:
        return "Occasional Buyers"
    return "At Risk"


class SegmentationModel:
    """K-Means with a frozen column contract; no retraining during inference."""

    def __init__(
        self,
        n_clusters: int = N_CLUSTERS,
        random_state: int = RANDOM_STATE,
        n_init: int = N_INIT,
    ) -> None:
        self.n_clusters = n_clusters
        self.preprocessor = FeaturePreprocessor(SEGMENT_FEATURES)
        self.model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=n_init)
        self._fitted = False

    def fit(self, matrix: np.ndarray) -> SegmentationModel:
        scaled = self.preprocessor.fit_transform(matrix)
        if scaled.shape[0] <= self.n_clusters:
            raise ValueError(f"need more than {self.n_clusters} samples, got {scaled.shape[0]}")
        self.model.fit(scaled)
        self._fitted = True
        return self

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise ValueError("SegmentationModel is not fitted")

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        self._require_fitted()
        if np.asarray(matrix).shape[1] != self.preprocessor.n_features:
            raise FeatureMismatchError(
                f"segmentation expects {self.preprocessor.n_features} columns"
            )
        return self.model.predict(self.preprocessor.transform(matrix))

    def silhouette(self, matrix: np.ndarray) -> float | None:
        self._require_fitted()
        scaled = self.preprocessor.transform(matrix)
        labels = self.model.predict(scaled)
        if len(set(labels.tolist())) < 2 or scaled.shape[0] <= self.n_clusters:
            return None
        return float(silhouette_score(scaled, labels))

    def summarize(
        self, matrix: np.ndarray, customer_ids: list[int]
    ) -> tuple[list[ClusterSummary], dict[int, int]]:
        self._require_fitted()
        labels = self.predict(matrix).tolist()
        assignments = dict(zip(customer_ids, labels, strict=True))
        original = self.preprocessor.inverse_transform(self.preprocessor.transform(matrix))
        recency_idx = SEGMENT_FEATURES.index("recency_days")
        orders_idx = SEGMENT_FEATURES.index("completed_orders")
        revenue_idx = SEGMENT_FEATURES.index("total_revenue")

        by_cluster: dict[int, list[int]] = {}
        for position, label in enumerate(labels):
            by_cluster.setdefault(int(label), []).append(position)

        med_orders = float(np.median(original[:, orders_idx])) if len(original) else 0.0
        med_revenue = float(np.median(original[:, revenue_idx])) if len(original) else 0.0

        summaries = []
        total = len(customer_ids)
        for cluster_id in sorted(by_cluster):
            positions = by_cluster[cluster_id]
            block = original[positions]
            avg_recency = float(np.mean(block[:, recency_idx]))
            avg_orders = float(np.mean(block[:, orders_idx]))
            avg_revenue = float(np.mean(block[:, revenue_idx]))
            summaries.append(
                ClusterSummary(
                    cluster_id=cluster_id,
                    size=len(positions),
                    share=len(positions) / total if total else 0.0,
                    avg_recency_days=avg_recency,
                    avg_completed_orders=avg_orders,
                    avg_revenue=avg_revenue,
                    business_label=label_cluster(
                        avg_recency, avg_orders, med_orders, med_revenue, avg_revenue
                    ),
                )
            )
        return summaries, assignments


def train_segmentation(
    db: Session,
    reference_date: datetime | None = None,
    history_days: int = 365,
    customer_ids: list[int] | None = None,
    n_clusters: int = N_CLUSTERS,
) -> tuple[SegmentationModel, SegmentationResult]:
    """Train on the feature layer; deterministic for fixed inputs."""
    records = build_customer_features(db, reference_date, history_days, customer_ids)
    if not records:
        raise ValueError("no customers to segment")
    matrix, ids = vectors_from_records(records, SEGMENT_FEATURES)
    model = SegmentationModel(n_clusters=n_clusters).fit(matrix)
    summaries, assignments = model.summarize(matrix, ids)
    result = SegmentationResult(
        n_clusters=n_clusters,
        silhouette=model.silhouette(matrix),
        inertia=float(model.model.inertia_),
        summaries=summaries,
        assignments=assignments,
    )
    return model, result


def bundle_segmentation(model: SegmentationModel, result: SegmentationResult) -> dict:
    return {
        "kind": "segmentation",
        "n_clusters": model.n_clusters,
        "random_state": RANDOM_STATE,
        "n_init": N_INIT,
        "feature_names": model.preprocessor.feature_names,
        "scaler": model.preprocessor.scaler,
        "kmeans": model.model,
        "summaries": [summary.model_dump() for summary in result.summaries],
        "silhouette": result.silhouette,
        "inertia": result.inertia,
    }


def load_segmentation(bundle: dict) -> SegmentationModel:
    model = SegmentationModel(n_clusters=int(bundle["n_clusters"]))
    model.preprocessor = FeaturePreprocessor(list(bundle["feature_names"]))
    model.preprocessor.scaler = bundle["scaler"]
    model.model = bundle["kmeans"]
    model._fitted = True
    return model
