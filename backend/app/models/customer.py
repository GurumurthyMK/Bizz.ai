"""Customer model — identity/profile foundation for all intelligence phases."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.interaction import Interaction
    from app.models.opportunity import Opportunity
    from app.models.prediction import Prediction
    from app.models.segment import Segment
    from app.models.transaction import Transaction


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("segments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer", lazy="selectin"
    )
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="customer", lazy="selectin"
    )
    segment: Mapped["Segment | None"] = relationship(back_populates="customers")
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="customer", lazy="selectin"
    )
    opportunities: Mapped[list["Opportunity"]] = relationship(
        back_populates="customer", lazy="selectin"
    )
