"""Prediction model — persisted churn/purchase probabilities per customer.

One row per (customer, prediction_type): materialization replaces the table,
so rows always represent the latest model output. Probabilities and signals
come verbatim from the trained models; nothing is invented here.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("customer_id", "prediction_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    prediction_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    band: Mapped[str] = mapped_column(String(10), nullable=False)
    signals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="predictions")

    def signal_list(self) -> list[str]:
        signals: Any = self.signals
        return list(signals) if isinstance(signals, list) else []
