"""Transaction business logic. Transactions are append-only facts."""

from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.common import MAX_PAGE_SIZE
from app.schemas.transaction import TransactionCreate, TransactionStatus
from app.services.errors import NotFoundError, ReferenceError
from app.services.pagination import normalize_pagination, paginate


def create_transaction(db: Session, data: TransactionCreate) -> Transaction:
    if db.get(Customer, data.customer_id) is None:
        raise ReferenceError("Customer", data.customer_id)
    if db.get(Product, data.product_id) is None:
        raise ReferenceError("Product", data.product_id)
    transaction = Transaction(
        customer_id=data.customer_id,
        product_id=data.product_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        discount=data.discount,
        total_amount=data.quantity * data.unit_price - data.discount,
        status=data.status,
        transaction_date=data.transaction_date,
        refunded_at=data.refunded_at,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction(db: Session, transaction_id: int) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise NotFoundError("Transaction", transaction_id)
    return transaction


TransactionSort = Literal["transaction_date", "total_amount", "id"]
SortOrder = Literal["asc", "desc"]


def list_transactions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    customer_id: int | None = None,
    product_id: int | None = None,
    status: TransactionStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: TransactionSort = "transaction_date",
    order: SortOrder = "desc",
) -> tuple[list[Transaction], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    column = {
        "transaction_date": Transaction.transaction_date,
        "total_amount": Transaction.total_amount,
        "id": Transaction.id,
    }[sort_by]
    stmt = select(Transaction).order_by(
        column.asc() if order == "asc" else column.desc(), Transaction.id
    )
    if customer_id is not None:
        stmt = stmt.where(Transaction.customer_id == customer_id)
    if product_id is not None:
        stmt = stmt.where(Transaction.product_id == product_id)
    if status is not None:
        stmt = stmt.where(Transaction.status == status)
    if date_from is not None:
        stmt = stmt.where(Transaction.transaction_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Transaction.transaction_date <= date_to)
    return paginate(stmt, db, page, page_size)
