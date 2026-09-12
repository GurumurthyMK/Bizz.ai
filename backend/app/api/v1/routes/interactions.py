"""Interaction endpoints. Interactions are append-only: no update or delete."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.interaction import (
    InteractionChannel,
    InteractionCreate,
    InteractionResponse,
    InteractionType,
)
from app.services import interactions as interaction_service
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/interactions",
    tags=["interactions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[InteractionResponse])
def list_interactions(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    customer_id: int | None = Query(default=None, gt=0),
    campaign_id: int | None = Query(default=None, gt=0),
    interaction_type: InteractionType | None = None,
    channel: InteractionChannel | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Page[InteractionResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = interaction_service.list_interactions(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        campaign_id=campaign_id,
        interaction_type=interaction_type,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
    )
    return Page[InteractionResponse](
        items=[InteractionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(
    data: InteractionCreate, db: Session = Depends(get_db)
) -> InteractionResponse:
    return InteractionResponse.model_validate(interaction_service.create_interaction(db, data))


@router.get("/{interaction_id}", response_model=InteractionResponse)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)) -> InteractionResponse:
    return InteractionResponse.model_validate(
        interaction_service.get_interaction(db, interaction_id)
    )
