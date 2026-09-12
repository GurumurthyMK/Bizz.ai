"""Alert response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Any] | None
    entity_type: str | None
    entity_id: int | None
    dedup_key: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None


class DetectionReport(BaseModel):
    reference_date: str
    evaluated: int
    created: int
    skipped_duplicates: int
