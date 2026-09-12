"""Opportunity endpoints: filtered lists plus detail."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.opportunity import OpportunityResponse
from app.services import opportunities as opportunity_service
from app.services.opportunities import OpportunitySort, SortOrder
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[OpportunityResponse])
def list_opportunities(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    tier: str | None = Query(default=None, max_length=10),
    opportunity_type: str | None = Query(default=None, max_length=30),
    customer_id: int | None = Query(default=None, gt=0),
    segment_id: int | None = Query(default=None, gt=0),
    min_score: float | None = Query(default=None, ge=0.0, le=1.0),
    sort_by: OpportunitySort = Query(default="score"),
    order: SortOrder = Query(default="desc"),
) -> Page[OpportunityResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = opportunity_service.list_opportunities(
        db,
        page=page,
        page_size=page_size,
        tier=tier,
        opportunity_type=opportunity_type,
        customer_id=customer_id,
        segment_id=segment_id,
        min_score=min_score,
        sort_by=sort_by,
        order=order,
    )
    return Page[OpportunityResponse](
        items=[OpportunityResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> OpportunityResponse:
    return OpportunityResponse.model_validate(
        opportunity_service.get_opportunity(db, opportunity_id)
    )
