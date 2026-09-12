"""Opportunity read workflows: filtered, sorted, paginated lists."""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.opportunity import Opportunity
from app.schemas.common import MAX_PAGE_SIZE
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate

OpportunitySort = Literal["score", "estimated_value", "customer_id"]
SortOrder = Literal["asc", "desc"]


def list_opportunities(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    tier: str | None = None,
    opportunity_type: str | None = None,
    customer_id: int | None = None,
    segment_id: int | None = None,
    min_score: float | None = None,
    sort_by: OpportunitySort = "score",
    order: SortOrder = "desc",
) -> tuple[list[Opportunity], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Opportunity)
    if tier is not None:
        stmt = stmt.where(Opportunity.tier == tier)
    if opportunity_type is not None:
        stmt = stmt.where(Opportunity.opportunity_type == opportunity_type)
    if customer_id is not None:
        stmt = stmt.where(Opportunity.customer_id == customer_id)
    if segment_id is not None:
        stmt = stmt.where(Opportunity.segment_id == segment_id)
    if min_score is not None:
        stmt = stmt.where(Opportunity.score >= min_score)
    column = {
        "score": Opportunity.score,
        "estimated_value": Opportunity.estimated_value,
        "customer_id": Opportunity.customer_id,
    }[sort_by]
    stmt = stmt.order_by(column.asc() if order == "asc" else column.desc())
    return paginate(stmt, db, page, page_size)


def get_opportunity(db: Session, opportunity_id: int) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise NotFoundError("Opportunity", opportunity_id)
    return opportunity
