"""Customer endpoints. All routes require authentication."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.customer import (
    CustomerCreate,
    CustomerIntelligenceResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.schemas.opportunity import OpportunityResponse
from app.schemas.prediction import PredictionResponse
from app.schemas.segment import SegmentResponse
from app.services import customers as customer_service
from app.services.customers import CustomerSort, SortOrder
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[CustomerResponse])
def list_customers(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(default=None, max_length=255),
    city: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_by: CustomerSort = Query(default="id"),
    order: SortOrder = Query(default="asc"),
) -> Page[CustomerResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = customer_service.list_customers(
        db,
        page=page,
        page_size=page_size,
        search=search,
        city=city,
        country=country,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        order=order,
    )
    return Page[CustomerResponse](
        items=[CustomerResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)) -> CustomerResponse:
    return CustomerResponse.model_validate(customer_service.create_customer(db, data))


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> CustomerResponse:
    return CustomerResponse.model_validate(customer_service.get_customer(db, customer_id))


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)
) -> CustomerResponse:
    return CustomerResponse.model_validate(customer_service.update_customer(db, customer_id, data))


@router.get("/{customer_id}/intelligence", response_model=CustomerIntelligenceResponse)
def get_customer_intelligence(
    customer_id: int,
    db: Session = Depends(get_db),
    reference_date: datetime | None = None,
    history_days: int = Query(default=365, ge=30, le=730),
) -> CustomerIntelligenceResponse:
    customer, metrics, predictions, opportunities = customer_service.get_customer_intelligence(
        db, customer_id, reference_date, history_days
    )
    return CustomerIntelligenceResponse(
        customer=CustomerResponse.model_validate(customer),
        metrics=metrics,
        segment=(
            SegmentResponse.model_validate(customer.segment)
            if customer.segment is not None
            else None
        ),
        predictions=[PredictionResponse.model_validate(item) for item in predictions],
        opportunities=[OpportunityResponse.model_validate(item) for item in opportunities],
    )
