"""SQLAlchemy declarative base and model foundation.

Business models for later phases (users, customers, products, ...) will
subclass ``Base`` and be imported in ``app.models`` so Alembic autogenerate
can discover them.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
