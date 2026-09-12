"""Interaction request/response schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InteractionType = Literal[
    "purchase", "click", "open", "visit", "call", "support", "review", "referral"
]
InteractionChannel = Literal["email", "sms", "social", "web", "store", "phone", "app"]


class InteractionCreate(BaseModel):
    customer_id: int = Field(gt=0)
    campaign_id: int | None = Field(default=None, gt=0)
    interaction_type: InteractionType
    channel: InteractionChannel
    occurred_at: datetime
    summary: str | None = Field(default=None, max_length=2000)
    extra: dict[str, Any] | None = None


class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    campaign_id: int | None
    interaction_type: str
    channel: str
    occurred_at: datetime
    summary: str | None
    extra: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
