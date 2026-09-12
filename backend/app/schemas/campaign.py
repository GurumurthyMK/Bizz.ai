"""Campaign request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CampaignChannel = Literal["email", "sms", "social", "ads", "push", "in_store"]
CampaignType = Literal["promotional", "awareness", "retention", "winback", "seasonal"]
CampaignStatus = Literal["draft", "active", "paused", "completed"]


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    channel: CampaignChannel
    campaign_type: CampaignType
    status: CampaignStatus = "draft"
    start_date: datetime | None = None
    end_date: datetime | None = None
    budget: Decimal | None = Field(default=None, ge=Decimal("0"))
    description: str | None = None

    @model_validator(mode="after")
    def end_cannot_precede_start(self) -> "CampaignCreate":
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date cannot be before start_date")
        return self


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    channel: CampaignChannel | None = None
    campaign_type: CampaignType | None = None
    status: CampaignStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    budget: Decimal | None = Field(default=None, ge=Decimal("0"))
    description: str | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    channel: str
    campaign_type: str
    status: str
    start_date: datetime | None
    end_date: datetime | None
    budget: Decimal | None
    description: str | None
    created_at: datetime
    updated_at: datetime
