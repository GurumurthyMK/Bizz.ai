"""Data management schemas: CSV preview/import, jobs, health."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DataEntity = Literal["customers", "products", "transactions", "campaigns", "interactions"]


class RowErrorResponse(BaseModel):
    line: int
    column: str
    message: str


class PreviewResponse(BaseModel):
    entity: str
    filename: str
    columns: list[str]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[RowErrorResponse]
    errors_truncated: bool
    sample: list[dict[str, Any]]


class ImportResultResponse(BaseModel):
    entity: str
    filename: str
    status: str
    rows_total: int
    rows_inserted: int
    rows_failed: int
    errors: list[RowErrorResponse]


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity: str
    filename: str
    rows_total: int
    rows_valid: int
    rows_inserted: int
    rows_failed: int
    status: str
    error_summary: list[dict[str, Any]] | None
    created_at: datetime


class HealthCounts(BaseModel):
    customers: int = Field(ge=0)
    products: int = Field(ge=0)
    transactions: int = Field(ge=0)
    campaigns: int = Field(ge=0)
    interactions: int = Field(ge=0)


class HealthMissing(BaseModel):
    customers_without_phone: int = Field(ge=0)
    customers_without_city: int = Field(ge=0)
    products_without_brand: int = Field(ge=0)


class HealthIntegrity(BaseModel):
    orphan_transactions: int = Field(ge=0)
    orphan_interactions: int = Field(ge=0)
    over_discounted_transactions: int = Field(ge=0)


class HealthFreshness(BaseModel):
    transaction_date_min: str | None = None
    transaction_date_max: str | None = None
    last_interaction_at: str | None = None


class HealthLastImport(BaseModel):
    entity: str
    status: str
    filename: str
    rows_total: int
    rows_inserted: int
    rows_failed: int
    created_at: str | None = None


class DataHealthResponse(BaseModel):
    counts: HealthCounts
    missing_values: HealthMissing
    integrity: HealthIntegrity
    freshness: HealthFreshness
    last_import: HealthLastImport | None = None
