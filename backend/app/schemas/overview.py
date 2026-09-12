"""Overview response contract: one coherent business-health payload.

Formulas:
- Every KPI compares the trailing 30-day window [ref-30d, ref] ("current")
  against the preceding 30 days ("previous").
- change_pct = (current - previous) / |previous| * 100, rounded to 1 decimal;
  None when previous == 0. direction is up/down/flat(new activity counts as
  up, no activity on either side as flat).
- Trend buckets are six consecutive 30-day periods ending at ref.
- Attention severities: high = revenue loss or large at-risk value exposure;
  medium = engagement/refund deterioration; ordered high-first, then by
  affected customers descending.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class KpiValue(BaseModel):
    label: str
    value: float
    previous_value: float
    change_pct: float | None
    direction: str = Field(pattern="^(up|down|flat)$")


class BusinessHealth(BaseModel):
    revenue: KpiValue
    active_customers: KpiValue
    transactions: KpiValue
    avg_order_value: KpiValue


class TrendBucket(BaseModel):
    period_start: str
    period_end: str
    revenue: float
    orders: int
    active_customers: int
    interactions: int


class InvestigationLink(BaseModel):
    label: str
    href: str
    kind: str = Field(pattern="^(section|entity)$")


class AttentionItem(BaseModel):
    id: str
    severity: str = Field(pattern="^(high|medium|low)$")
    title: str
    description: str
    affected_customers: int
    metric_value: float | None = None
    metric_label: str | None = None
    links: list[InvestigationLink] = Field(default_factory=list)


class OpportunityItem(BaseModel):
    customer_id: int
    score: float
    tier: str
    reasons: list[str]
    links: list[InvestigationLink] = Field(default_factory=list)


class OverviewMeta(BaseModel):
    reference_date: str
    history_days: int
    ml_available: bool
    customer_count: int


class OverviewResponse(BaseModel):
    meta: OverviewMeta
    health: BusinessHealth
    trends: list[TrendBucket]
    attention: list[AttentionItem]
    opportunities: list[OpportunityItem]
