"""Prediction read workflows: filtered, sorted, paginated lists."""

from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.schemas.common import MAX_PAGE_SIZE
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate

PredictionType = Literal["churn", "purchase"]
PredictionSort = Literal["probability", "customer_id"]
SortOrder = Literal["asc", "desc"]


def list_predictions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    prediction_type: PredictionType | None = None,
    band: str | None = None,
    customer_id: int | None = None,
    min_probability: float | None = None,
    sort_by: PredictionSort = "probability",
    order: SortOrder = "desc",
) -> tuple[list[Prediction], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Prediction)
    if prediction_type is not None:
        stmt = stmt.where(Prediction.prediction_type == prediction_type)
    if band is not None:
        stmt = stmt.where(Prediction.band == band)
    if customer_id is not None:
        stmt = stmt.where(Prediction.customer_id == customer_id)
    if min_probability is not None:
        stmt = stmt.where(Prediction.probability >= min_probability)
    column = Prediction.probability if sort_by == "probability" else Prediction.customer_id
    stmt = stmt.order_by(column.asc() if order == "asc" else column.desc())
    return paginate(stmt, db, page, page_size)


def get_prediction(db: Session, prediction_id: int) -> Prediction:
    prediction = db.get(Prediction, prediction_id)
    if prediction is None:
        raise NotFoundError("Prediction", prediction_id)
    return prediction
