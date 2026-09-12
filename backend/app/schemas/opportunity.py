"""Opportunity response schemas (persisted deterministic scores)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class OpportunityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    segment_id: int | None
    opportunity_type: str
    score: float
    tier: str
    estimated_value: Decimal
    reasons: list[str] | None
    signals: dict[str, Any] | None
    recommended_action: str
    model_version: str
    reference_date: datetime
    created_at: datetime
