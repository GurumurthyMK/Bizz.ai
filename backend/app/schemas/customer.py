"""Customer request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.analytics.customers import CustomerMetrics
from app.schemas.opportunity import OpportunityResponse
from app.schemas.prediction import PredictionResponse
from app.schemas.segment import SegmentResponse


class CustomerCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class CustomerUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None
    city: str | None
    country: str | None
    created_at: datetime
    updated_at: datetime


class CustomerIntelligenceResponse(BaseModel):
    """360° customer intelligence: profile, metrics, segment, predictions,
    opportunities — all from persisted or computed backend outputs."""

    customer: CustomerResponse
    metrics: CustomerMetrics
    segment: SegmentResponse | None
    predictions: list[PredictionResponse]
    opportunities: list[OpportunityResponse]
