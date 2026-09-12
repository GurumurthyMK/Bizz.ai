"""Opportunity model — persisted deterministic opportunity scores.

Each row explains itself: score plus tier, type, estimated value, reasons,
component signals, and a recommended action. Scores come verbatim from the
deterministic opportunity engine; only customers at or above
``OPPORTUNITY_MIN_SCORE`` are persisted.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.segment import Segment


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("segments.id"), nullable=True, index=True
    )
    opportunity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(10), nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    signals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="opportunities")
    segment: Mapped["Segment | None"] = relationship(back_populates="opportunities")

    def reason_list(self) -> list[str]:
        reasons: Any = self.reasons
        return list(reasons) if isinstance(reasons, list) else []
