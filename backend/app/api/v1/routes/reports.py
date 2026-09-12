"""Report endpoint: on-demand business reports over verified data."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.routes.ai import get_llm_provider
from app.db.session import get_db
from app.llm.provider import LLMProvider
from app.schemas.report import ReportResponse
from app.services import reports as report_service

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    db: Session = Depends(get_db),
    reference_date: datetime | None = None,
    history_days: int = Query(default=365, ge=30, le=730),
    include_narrative: bool = Query(default=True),
    provider: LLMProvider | None = Depends(get_llm_provider),
) -> ReportResponse:
    """Assemble the full report. Narrative is included when requested and a
    provider is available; factual sections are always complete."""
    return report_service.generate_report(
        db,
        reference_date,
        history_days,
        artifacts_dir=None,
        llm_provider=provider if include_narrative else None,
    )
