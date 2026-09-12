"""Transaction endpoints. Transactions are append-only: no update or delete."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionStatus,
)
from app.services import transactions as transaction_service
from app.services.pagination import normalize_pagination
from app.services.transactions import SortOrder, TransactionSort

router = APIRouter(
    prefix="/transactions",
    tags=["transactions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    customer_id: int | None = Query(default=None, gt=0),
    product_id: int | None = Query(default=None, gt=0),
    status: TransactionStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: TransactionSort = Query(default="transaction_date"),
    order: SortOrder = Query(default="desc"),
) -> Page[TransactionResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = transaction_service.list_transactions(
        db,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        product_id=product_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        order=order,
    )
    return Page[TransactionResponse](
        items=[TransactionResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate, db: Session = Depends(get_db)
) -> TransactionResponse:
    return TransactionResponse.model_validate(transaction_service.create_transaction(db, data))


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)) -> TransactionResponse:
    return TransactionResponse.model_validate(
        transaction_service.get_transaction(db, transaction_id)
    )
