"""Campaign analytics: funnel, conversion, attributed revenue, ROI, comparisons.

The data model records observed engagement (open/click/purchase interactions
optionally linked to a campaign) — not message sends or deliveries. The
funnel is therefore computed bottom-up from what was observed:

- reached: distinct customers with any interaction linked to the campaign
- opened/clicked/converted: distinct customers with that linked event type
  (converted = linked ``purchase`` interaction)
- revenue: completed transactions by converted customers inside the campaign
  window (documented attribution heuristic)
- ROI: (revenue - budget) / budget; None when budget is missing or zero

Rates are None when their denominator is zero — never fabricated.
"""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.interaction import Interaction
from app.models.transaction import Transaction


class CampaignMetrics(BaseModel):
    campaign_id: int
    name: str
    channel: str
    campaign_type: str
    status: str
    reached: int
    opened: int
    clicked: int
    converted: int
    open_rate: float | None
    click_rate: float | None
    click_to_open_rate: float | None
    conversion_rate: float | None
    attributed_revenue: float
    budget: float | None
    roi: float | None


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def compute_campaign_metrics(
    db: Session, campaign_ids: list[int] | None = None
) -> list[CampaignMetrics]:
    id_filter = [Campaign.id.in_(campaign_ids)] if campaign_ids else []
    event_filter = [Interaction.campaign_id.in_(campaign_ids)] if campaign_ids else []
    campaigns = db.execute(select(Campaign).where(*id_filter)).scalars().all()

    funnel_rows = db.execute(
        select(
            Interaction.campaign_id,
            func.count(func.distinct(Interaction.customer_id)).label("reached"),
            func.count(
                func.distinct(
                    case((Interaction.interaction_type == "open", Interaction.customer_id))
                )
            ).label("opened"),
            func.count(
                func.distinct(
                    case((Interaction.interaction_type == "click", Interaction.customer_id))
                )
            ).label("clicked"),
            func.count(
                func.distinct(
                    case((Interaction.interaction_type == "purchase", Interaction.customer_id))
                )
            ).label("converted"),
        )
        .where(
            Interaction.campaign_id.is_not(None),
            *event_filter,
        )
        .group_by(Interaction.campaign_id)
    ).all()
    funnel = {int(row[0]): row for row in funnel_rows}

    converted_customers: dict[int, list[int]] = {}
    conv_rows = db.execute(
        select(Interaction.campaign_id, Interaction.customer_id)
        .where(
            Interaction.campaign_id.is_not(None),
            Interaction.interaction_type == "purchase",
            *event_filter,
        )
        .distinct()
    ).all()
    for campaign_id, customer_id in conv_rows:
        converted_customers.setdefault(int(campaign_id), []).append(int(customer_id))

    metrics = []
    for campaign in campaigns:
        row = funnel.get(campaign.id)
        reached = int(row[1] or 0) if row else 0
        opened = int(row[2] or 0) if row else 0
        clicked = int(row[3] or 0) if row else 0
        converted = int(row[4] or 0) if row else 0

        customers = converted_customers.get(campaign.id, [])
        revenue = 0.0
        if customers:
            conditions = [
                Transaction.customer_id.in_(customers),
                Transaction.status == "completed",
            ]
            if campaign.start_date is not None:
                conditions.append(Transaction.transaction_date >= campaign.start_date)
            if campaign.end_date is not None:
                conditions.append(Transaction.transaction_date <= campaign.end_date)
            revenue = float(
                db.scalar(select(func.sum(Transaction.total_amount)).where(*conditions)) or 0
            )

        budget = float(campaign.budget) if campaign.budget is not None else None
        roi = (revenue - budget) / budget if budget else None

        metrics.append(
            CampaignMetrics(
                campaign_id=campaign.id,
                name=campaign.name,
                channel=campaign.channel,
                campaign_type=campaign.campaign_type,
                status=campaign.status,
                reached=reached,
                opened=opened,
                clicked=clicked,
                converted=converted,
                open_rate=_rate(opened, reached),
                click_rate=_rate(clicked, reached),
                click_to_open_rate=_rate(clicked, opened),
                conversion_rate=_rate(converted, reached),
                attributed_revenue=revenue,
                budget=budget,
                roi=roi,
            )
        )
    return metrics


def compare_campaigns(metrics: list[CampaignMetrics]) -> list[CampaignMetrics]:
    """Rank campaigns by ROI; campaigns without ROI sort last, id breaks ties."""
    return sorted(
        metrics,
        key=lambda m: (
            m.roi is None,
            -(m.roi if m.roi is not None else 0.0),
            m.campaign_id,
        ),
    )


__all__ = ["CampaignMetrics", "compare_campaigns", "compute_campaign_metrics"]
