"""Overview endpoint: one coherent business-health response."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.overview import OverviewResponse
from app.services import overview as overview_service

router = APIRouter(
    prefix="/overview",
    tags=["overview"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=OverviewResponse)
def get_overview(
    db: Session = Depends(get_db),
    reference_date: datetime | None = None,
    history_days: int = Query(default=365, ge=30, le=730),
    attention_limit: int = Query(default=5, ge=1, le=20),
    opportunity_limit: int = Query(default=5, ge=1, le=20),
) -> OverviewResponse:
    # Models are loaded from the default artifacts directory; a missing
    # artifact degrades ML sections honestly instead of failing the endpoint.
    return overview_service.get_overview(
        db,
        reference_date=reference_date,
        history_days=history_days,
        artifacts_dir=None,
        attention_limit=attention_limit,
        opportunity_limit=opportunity_limit,
    )
