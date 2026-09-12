"""Report response schemas. Facts come from services; narrative is optional."""

from pydantic import BaseModel, ConfigDict

from app.schemas.opportunity import OpportunityResponse
from app.schemas.overview import BusinessHealth, TrendBucket
from app.schemas.prediction import PredictionResponse
from app.schemas.segment import SegmentResponse


class RecommendationItem(BaseModel):
    title: str
    detail: str
    priority: str


class ReportNarrative(BaseModel):
    executive_summary: str | None = None
    recommendations: str | None = None
    model: str | None = None
    provider: str | None = None


class ReportPredictionBlock(BaseModel):
    churn_high_count: int
    purchase_high_count: int
    top_churn: list[PredictionResponse]
    top_purchase: list[PredictionResponse]


class ReportOpportunityBlock(BaseModel):
    total: int
    high_count: int
    top: list[OpportunityResponse]


class ReportMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reference_date: str
    history_days: int
    llm_available: bool
    customer_count: int


class ReportResponse(BaseModel):
    meta: ReportMeta
    executive_summary: str
    key_metrics: BusinessHealth
    customer_trends: list[TrendBucket]
    segments: list[SegmentResponse]
    predictions: ReportPredictionBlock
    opportunities: ReportOpportunityBlock
    recommendations: list[RecommendationItem]
    narrative: ReportNarrative
