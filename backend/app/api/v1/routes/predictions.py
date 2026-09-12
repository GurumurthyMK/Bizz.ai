"""Prediction endpoints: filtered lists plus detail."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.prediction import PredictionResponse
from app.services import predictions as prediction_service
from app.services.pagination import normalize_pagination
from app.services.predictions import PredictionSort, PredictionType, SortOrder

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[PredictionResponse])
def list_predictions(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    prediction_type: PredictionType | None = None,
    band: str | None = Query(default=None, max_length=10),
    customer_id: int | None = Query(default=None, gt=0),
    min_probability: float | None = Query(default=None, ge=0.0, le=1.0),
    sort_by: PredictionSort = Query(default="probability"),
    order: SortOrder = Query(default="desc"),
) -> Page[PredictionResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = prediction_service.list_predictions(
        db,
        page=page,
        page_size=page_size,
        prediction_type=prediction_type,
        band=band,
        customer_id=customer_id,
        min_probability=min_probability,
        sort_by=sort_by,
        order=order,
    )
    return Page[PredictionResponse](
        items=[PredictionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(prediction_id: int, db: Session = Depends(get_db)) -> PredictionResponse:
    return PredictionResponse.model_validate(prediction_service.get_prediction(db, prediction_id))
