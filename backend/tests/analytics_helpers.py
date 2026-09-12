"""Shared ORM builders for analytics tests (explicit ids via returned objects)."""

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.interaction import Interaction
from app.models.product import Product
from app.models.transaction import Transaction

REF = datetime(2026, 9, 1, tzinfo=UTC)


def at(day: date, hour: int = 10) -> datetime:
    """Build an aware UTC datetime from a date (test shorthand)."""
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def add_customer(
    db: Session,
    unique: str,
    tag: str = "c",
    city: str | None = None,
    country: str | None = None,
) -> Customer:
    customer = Customer(
        first_name="Test",
        last_name=tag,
        email=f"{tag}-{unique}@example.com",
        city=city,
        country=country,
    )
    db.add(customer)
    db.flush()
    return customer


def add_product(
    db: Session,
    unique: str,
    tag: str = "p",
    unit_price: float = 25.00,
    category: str = "Gadgets",
    brand: str | None = "Acme",
) -> Product:
    product = Product(
        sku=f"SKU-{tag}-{unique}",
        name=f"Item {tag}",
        category=category,
        brand=brand,
        unit_price=unit_price,
    )
    db.add(product)
    db.flush()
    return product


def add_txn(
    db: Session,
    customer_id: int,
    product_id: int,
    moment: datetime,
    quantity: int = 1,
    unit_price: float = 10.00,
    discount: float = 0.00,
    status: str = "completed",
) -> Transaction:
    gross = round(quantity * unit_price, 2)
    txn = Transaction(
        customer_id=customer_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
        discount=discount,
        total_amount=round(gross - discount, 2),
        status=status,
        transaction_date=moment,
    )
    db.add(txn)
    db.flush()
    return txn


def add_campaign(
    db: Session,
    unique: str,
    tag: str = "m",
    channel: str = "email",
    status: str = "completed",
    budget: float | None = 1000.00,
) -> Campaign:
    campaign = Campaign(
        name=f"Campaign {tag}-{unique}",
        channel=channel,
        campaign_type="promotional",
        status=status,
        budget=budget,
    )
    db.add(campaign)
    db.flush()
    return campaign


def add_event(
    db: Session,
    customer_id: int,
    moment: datetime,
    itype: str = "visit",
    channel: str = "web",
    campaign_id: int | None = None,
) -> Interaction:
    event = Interaction(
        customer_id=customer_id,
        campaign_id=campaign_id,
        interaction_type=itype,
        channel=channel,
        occurred_at=moment,
    )
    db.add(event)
    db.flush()
    return event
