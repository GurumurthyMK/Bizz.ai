"""Campaign business logic."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignStatus, CampaignUpdate
from app.schemas.common import MAX_PAGE_SIZE
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate


def create_campaign(db: Session, data: CampaignCreate) -> Campaign:
    campaign = Campaign(
        name=data.name.strip(),
        channel=data.channel,
        campaign_type=data.campaign_type,
        status=data.status,
        start_date=data.start_date,
        end_date=data.end_date,
        budget=data.budget,
        description=data.description,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def get_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign", campaign_id)
    return campaign


def list_campaigns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    channel: str | None = None,
    status: CampaignStatus | None = None,
) -> tuple[list[Campaign], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Campaign).order_by(Campaign.id)
    if search:
        stmt = stmt.where(Campaign.name.ilike(f"%{search.strip()}%"))
    if channel:
        stmt = stmt.where(Campaign.channel == channel)
    if status is not None:
        stmt = stmt.where(Campaign.status == status)
    return paginate(stmt, db, page, page_size)


def update_campaign(db: Session, campaign_id: int, data: CampaignUpdate) -> Campaign:
    campaign = get_campaign(db, campaign_id)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") is not None:
        changes["name"] = changes["name"].strip()
    for field, value in changes.items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return campaign
