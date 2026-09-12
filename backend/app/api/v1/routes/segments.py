"""Segment endpoints: list, detail, and member customers."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.customer import CustomerResponse
from app.schemas.segment import SegmentResponse
from app.services import segments as segment_service
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/segments",
    tags=["segments"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[SegmentResponse])
def list_segments(db: Session = Depends(get_db)) -> list[SegmentResponse]:
    return [SegmentResponse.model_validate(item) for item in segment_service.list_segments(db)]


@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(segment_id: int, db: Session = Depends(get_db)) -> SegmentResponse:
    return SegmentResponse.model_validate(segment_service.get_segment(db, segment_id))


@router.get("/{segment_id}/customers", response_model=Page[CustomerResponse])
def list_segment_customers(
    segment_id: int,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[CustomerResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = segment_service.list_segment_customers(
        db, segment_id, page=page, page_size=page_size
    )
    return Page[CustomerResponse](
        items=[CustomerResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
