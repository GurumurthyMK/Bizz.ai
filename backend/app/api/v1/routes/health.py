"""Health endpoints.

GET /api/v1/health    — basic application liveness, no database access.
GET /api/v1/health/db — database connectivity verification (SELECT 1).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import DbHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )


@router.get("/health/db", response_model=DbHealthResponse)
def health_db(db: Session = Depends(get_db)) -> DbHealthResponse:
    # Raises on connection failure; handled globally as a 503 without
    # leaking internals (see app.main.db_exception_handler).
    db.execute(text("SELECT 1"))
    return DbHealthResponse(status="ok", database="connected")
