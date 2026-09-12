"""Segment read workflows: list, detail, and member customers."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.segment import Segment
from app.schemas.common import MAX_PAGE_SIZE
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate


def list_segments(db: Session) -> list[Segment]:
    return list(db.scalars(select(Segment).order_by(Segment.id)).all())


def get_segment(db: Session, segment_id: int) -> Segment:
    segment = db.get(Segment, segment_id)
    if segment is None:
        raise NotFoundError("Segment", segment_id)
    return segment


def list_segment_customers(
    db: Session,
    segment_id: int,
    *,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Customer], int]:
    get_segment(db, segment_id)
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Customer).where(Customer.segment_id == segment_id).order_by(Customer.id)
    return paginate(stmt, db, page, page_size)


def count_segment_customers(db: Session, segment_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Customer).where(Customer.segment_id == segment_id)
        )
        or 0
    )
