"""Alert endpoints: detection, listing, detail, acknowledgement."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.alert import AlertResponse, DetectionReport
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.services import alerts as alert_service
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/detect", response_model=DetectionReport)
def detect_alerts(
    db: Session = Depends(get_db),
    reference_date: datetime | None = None,
) -> DetectionReport:
    report = alert_service.materialize_alerts(db, reference_date)
    return DetectionReport(**report)


@router.get("", response_model=Page[AlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    alert_type: str | None = Query(default=None, max_length=30),
    severity: str | None = Query(default=None, max_length=10),
    status: str | None = Query(default=None, max_length=20),
    entity_type: str | None = Query(default=None, max_length=30),
) -> Page[AlertResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = alert_service.list_alerts(
        db,
        page=page,
        page_size=page_size,
        alert_type=alert_type,
        severity=severity,
        status=status,
        entity_type=entity_type,
    )
    return Page[AlertResponse](
        items=[AlertResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    return AlertResponse.model_validate(alert_service.get_alert(db, alert_id))


@router.patch("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertResponse:
    return AlertResponse.model_validate(alert_service.acknowledge_alert(db, alert_id))
