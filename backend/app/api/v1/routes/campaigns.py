"""Campaign endpoints. All routes require authentication."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatus,
    CampaignUpdate,
)
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.services import campaigns as campaign_service
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/campaigns",
    tags=["campaigns"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[CampaignResponse])
def list_campaigns(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(default=None, max_length=255),
    channel: str | None = Query(default=None, max_length=50),
    status: CampaignStatus | None = None,
) -> Page[CampaignResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = campaign_service.list_campaigns(
        db,
        page=page,
        page_size=page_size,
        search=search,
        channel=channel,
        status=status,
    )
    return Page[CampaignResponse](
        items=[CampaignResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignCreate, db: Session = Depends(get_db)) -> CampaignResponse:
    return CampaignResponse.model_validate(campaign_service.create_campaign(db, data))


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)) -> CampaignResponse:
    return CampaignResponse.model_validate(campaign_service.get_campaign(db, campaign_id))


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int, data: CampaignUpdate, db: Session = Depends(get_db)
) -> CampaignResponse:
    return CampaignResponse.model_validate(campaign_service.update_campaign(db, campaign_id, data))
