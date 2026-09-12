"""ML package: training, persistence, and inference (no LLM involvement)."""

from app.ml import (
    churn,
    inference,
    labels,
    opportunity,
    persistence,
    preprocessing,
    purchase,
    segmentation,
    supervised,
)

__all__ = [
    "churn",
    "inference",
    "labels",
    "opportunity",
    "persistence",
    "preprocessing",
    "purchase",
    "segmentation",
    "supervised",
]
