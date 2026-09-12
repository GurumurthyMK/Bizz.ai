"""Transaction request/response schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TransactionStatus = Literal["completed", "pending", "refunded", "cancelled"]


class TransactionCreate(BaseModel):
    customer_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=Decimal("0"))
    discount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    status: TransactionStatus = "completed"
    transaction_date: datetime
    refunded_at: datetime | None = None

    @model_validator(mode="after")
    def discount_cannot_exceed_gross(self) -> "TransactionCreate":
        if self.discount > self.quantity * self.unit_price:
            raise ValueError("discount cannot exceed quantity * unit_price")
        return self


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    discount: Decimal
    total_amount: Decimal
    status: str
    transaction_date: datetime
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime
