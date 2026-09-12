"""Pydantic schemas package."""

from .ai import AIContextRef, AIResponse, AskRequest, InsightRequest, SummarizeRequest
from .alert import AlertResponse, DetectionReport
from .auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from .campaign import (
    CampaignChannel,
    CampaignCreate,
    CampaignResponse,
    CampaignStatus,
    CampaignType,
    CampaignUpdate,
)
from .common import MAX_PAGE_SIZE, Page
from .customer import CustomerCreate, CustomerIntelligenceResponse, CustomerResponse, CustomerUpdate
from .data import (
    DataEntity,
    DataHealthResponse,
    HealthCounts,
    HealthFreshness,
    HealthIntegrity,
    HealthLastImport,
    HealthMissing,
    ImportJobResponse,
    ImportResultResponse,
    PreviewResponse,
    RowErrorResponse,
)
from .health import DbHealthResponse, HealthResponse
from .interaction import (
    InteractionChannel,
    InteractionCreate,
    InteractionResponse,
    InteractionType,
)
from .opportunity import OpportunityResponse
from .overview import (
    AttentionItem,
    BusinessHealth,
    InvestigationLink,
    KpiValue,
    OpportunityItem,
    OverviewMeta,
    OverviewResponse,
    TrendBucket,
)
from .prediction import PredictionResponse
from .product import ProductCreate, ProductResponse, ProductUpdate
from .report import (
    RecommendationItem,
    ReportMeta,
    ReportNarrative,
    ReportOpportunityBlock,
    ReportPredictionBlock,
    ReportResponse,
)
from .segment import SegmentResponse
from .transaction import TransactionCreate, TransactionResponse, TransactionStatus

__all__ = [
    "AIContextRef",
    "AIResponse",
    "AlertResponse",
    "AskRequest",
    "AuthResponse",
    "AttentionItem",
    "BusinessHealth",
    "CampaignChannel",
    "CampaignCreate",
    "CampaignResponse",
    "CampaignStatus",
    "CampaignType",
    "CampaignUpdate",
    "CustomerCreate",
    "CustomerIntelligenceResponse",
    "CustomerResponse",
    "CustomerUpdate",
    "DataEntity",
    "DataHealthResponse",
    "DbHealthResponse",
    "DetectionReport",
    "HealthCounts",
    "HealthFreshness",
    "HealthIntegrity",
    "HealthLastImport",
    "HealthMissing",
    "HealthResponse",
    "ImportJobResponse",
    "ImportResultResponse",
    "InteractionChannel",
    "InteractionCreate",
    "InteractionResponse",
    "InteractionType",
    "InsightRequest",
    "InvestigationLink",
    "KpiValue",
    "LoginRequest",
    "MAX_PAGE_SIZE",
    "OpportunityItem",
    "OpportunityResponse",
    "OverviewMeta",
    "OverviewResponse",
    "Page",
    "PredictionResponse",
    "PreviewResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "RegisterRequest",
    "RecommendationItem",
    "ReportMeta",
    "ReportNarrative",
    "ReportOpportunityBlock",
    "ReportPredictionBlock",
    "ReportResponse",
    "RowErrorResponse",
    "SegmentResponse",
    "SummarizeRequest",
    "TransactionCreate",
    "TransactionResponse",
    "TransactionStatus",
    "TrendBucket",
    "UserResponse",
]
