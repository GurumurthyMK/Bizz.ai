"""Prediction response schemas (persisted model probabilities)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    prediction_type: str
    probability: float
    band: str
    signals: list[str] | None
    model_version: str
    reference_date: datetime
    created_at: datetime
