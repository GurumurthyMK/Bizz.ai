"""Segment model — one row per cluster of the latest materialization run.

Segments are replaced (never appended) on every materialization, so the
table always reflects the current model output. ``cluster_id`` is unique
to enforce the single-run invariant.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.opportunity import Opportunity


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cluster_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    share: Mapped[float] = mapped_column(Float, nullable=False)
    avg_recency_days: Mapped[float] = mapped_column(Float, nullable=False)
    avg_completed_orders: Mapped[float] = mapped_column(Float, nullable=False)
    avg_revenue: Mapped[float] = mapped_column(Float, nullable=False)
    silhouette: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customers: Mapped[list["Customer"]] = relationship(back_populates="segment", lazy="selectin")
    opportunities: Mapped[list["Opportunity"]] = relationship(
        back_populates="segment", lazy="selectin"
    )
