"""Segment response schemas (persisted cluster summaries)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cluster_id: int
    name: str
    size: int
    share: float
    avg_recency_days: float
    avg_completed_orders: float
    avg_revenue: float
    silhouette: float | None
    model_version: str
    reference_date: datetime
    created_at: datetime
