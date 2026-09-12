"""Intelligence endpoints: materialize model outputs, inspect status."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.services.intelligence import (
    IntelligenceStatus,
    MaterializationReport,
    get_intelligence_status,
    materialize_intelligence,
)

router = APIRouter(
    prefix="/intelligence",
    tags=["intelligence"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/status", response_model=IntelligenceStatus)
def intelligence_status(db: Session = Depends(get_db)) -> IntelligenceStatus:
    return get_intelligence_status(db)


@router.post("/materialize", response_model=MaterializationReport)
def materialize(
    db: Session = Depends(get_db),
    reference_date: datetime | None = None,
    history_days: int = Query(default=365, ge=30, le=730),
) -> MaterializationReport:
    """Persist the latest analytics/ML outputs into segments, predictions,
    and opportunities. Replaces previous output; reruns are idempotent."""
    return materialize_intelligence(db, reference_date, history_days)
