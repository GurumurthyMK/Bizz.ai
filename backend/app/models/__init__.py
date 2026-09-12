"""SQLAlchemy ORM models."""

from app.db.base import Base  # noqa: F401  (re-exported for Alembic discovery)
from app.models.alert import Alert  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.import_job import ImportJob  # noqa: F401
from app.models.interaction import Interaction  # noqa: F401
from app.models.opportunity import Opportunity  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.segment import Segment  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = [
    "Alert",
    "Base",
    "Campaign",
    "Customer",
    "ImportJob",
    "Interaction",
    "Opportunity",
    "Prediction",
    "Product",
    "Segment",
    "Transaction",
    "User",
]
