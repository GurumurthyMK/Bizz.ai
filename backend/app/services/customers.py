"""Customer business logic. Routes stay thin; rules live here."""

from datetime import datetime
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.analytics.customers import CustomerMetrics, get_customer_metrics
from app.models.customer import Customer
from app.models.opportunity import Opportunity
from app.models.prediction import Prediction
from app.schemas.common import MAX_PAGE_SIZE
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.errors import NotFoundError
from app.services.pagination import normalize_pagination, paginate


def create_customer(db: Session, data: CustomerCreate) -> Customer:
    customer = Customer(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        email=data.email.lower(),
        phone=data.phone,
        city=data.city,
        country=data.country,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer", customer_id)
    return customer


CustomerSort = Literal["id", "first_name", "last_name", "email", "created_at"]
SortOrder = Literal["asc", "desc"]


def list_customers(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    city: str | None = None,
    country: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_by: CustomerSort = "id",
    order: SortOrder = "asc",
) -> tuple[list[Customer], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    column = {
        "id": Customer.id,
        "first_name": Customer.first_name,
        "last_name": Customer.last_name,
        "email": Customer.email,
        "created_at": Customer.created_at,
    }[sort_by]
    stmt = select(Customer).order_by(column.asc() if order == "asc" else column.desc())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Customer.first_name.ilike(like),
                Customer.last_name.ilike(like),
                Customer.email.ilike(like),
            )
        )
    if city:
        stmt = stmt.where(Customer.city == city)
    if country:
        stmt = stmt.where(Customer.country == country)
    if created_from is not None:
        stmt = stmt.where(Customer.created_at >= created_from)
    if created_to is not None:
        stmt = stmt.where(Customer.created_at <= created_to)
    return paginate(stmt, db, page, page_size)


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> Customer:
    customer = get_customer(db, customer_id)
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"] is not None:
        changes["email"] = changes["email"].lower()
    for field in ("first_name", "last_name"):
        if changes.get(field) is not None:
            changes[field] = changes[field].strip()
    for field, value in changes.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


def get_customer_intelligence(
    db: Session,
    customer_id: int,
    reference_date: datetime | None = None,
    history_days: int = 365,
) -> tuple[Customer, CustomerMetrics, list[Prediction], list[Opportunity]]:
    """360° intelligence: profile (with segment), computed metrics, persisted
    predictions and opportunities. Segment/predictions/opportunities are empty
    until intelligence is materialized — metrics always compute live."""
    customer = get_customer(db, customer_id)
    metrics = get_customer_metrics(db, customer_id, reference_date, history_days)
    predictions = list(
        db.scalars(
            select(Prediction)
            .where(Prediction.customer_id == customer_id)
            .order_by(Prediction.prediction_type)
        ).all()
    )
    opportunities = list(
        db.scalars(
            select(Opportunity)
            .where(Opportunity.customer_id == customer_id)
            .order_by(Opportunity.score.desc())
        ).all()
    )
    return customer, metrics, predictions, opportunities
