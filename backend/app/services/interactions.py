"""Interaction business logic. Interactions are append-only events."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.schemas.common import MAX_PAGE_SIZE
from app.schemas.interaction import InteractionChannel, InteractionCreate, InteractionType
from app.services.errors import NotFoundError, ReferenceError
from app.services.pagination import normalize_pagination, paginate


def create_interaction(db: Session, data: InteractionCreate) -> Interaction:
    if db.get(Customer, data.customer_id) is None:
        raise ReferenceError("Customer", data.customer_id)
    if data.campaign_id is not None and db.get(Campaign, data.campaign_id) is None:
        raise ReferenceError("Campaign", data.campaign_id)
    interaction = Interaction(
        customer_id=data.customer_id,
        campaign_id=data.campaign_id,
        interaction_type=data.interaction_type,
        channel=data.channel,
        occurred_at=data.occurred_at,
        summary=data.summary,
        extra=data.extra,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    return interaction


def get_interaction(db: Session, interaction_id: int) -> Interaction:
    interaction = db.get(Interaction, interaction_id)
    if interaction is None:
        raise NotFoundError("Interaction", interaction_id)
    return interaction


def list_interactions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    customer_id: int | None = None,
    campaign_id: int | None = None,
    interaction_type: InteractionType | None = None,
    channel: InteractionChannel | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Interaction], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Interaction).order_by(Interaction.occurred_at.desc(), Interaction.id)
    if customer_id is not None:
        stmt = stmt.where(Interaction.customer_id == customer_id)
    if campaign_id is not None:
        stmt = stmt.where(Interaction.campaign_id == campaign_id)
    if interaction_type is not None:
        stmt = stmt.where(Interaction.interaction_type == interaction_type)
    if channel is not None:
        stmt = stmt.where(Interaction.channel == channel)
    if date_from is not None:
        stmt = stmt.where(Interaction.occurred_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(Interaction.occurred_at <= date_to)
    return paginate(stmt, db, page, page_size)
