"""Shared pagination helper for list services."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def normalize_pagination(page: int, page_size: int, max_page_size: int) -> tuple[int, int]:
    page = max(page, 1)
    return page, min(max(page_size, 1), max_page_size)


def paginate(stmt: Select, db: Session, page: int, page_size: int) -> tuple[list, int]:
    """Return (items, total) for a select statement without mutating it."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all())
    return items, total
