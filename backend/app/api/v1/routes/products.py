"""Product endpoints. All routes require authentication."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import products as product_service
from app.services.pagination import normalize_pagination

router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=Page[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
    search: str | None = Query(default=None, max_length=255),
    category: str | None = Query(default=None, max_length=100),
    brand: str | None = Query(default=None, max_length=100),
    is_active: bool | None = None,
) -> Page[ProductResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = product_service.list_products(
        db,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        brand=brand,
        is_active=is_active,
    )
    return Page[ProductResponse](
        items=[ProductResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> ProductResponse:
    return ProductResponse.model_validate(product_service.create_product(db, data))


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductResponse:
    return ProductResponse.model_validate(product_service.get_product(db, product_id))


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int, data: ProductUpdate, db: Session = Depends(get_db)
) -> ProductResponse:
    return ProductResponse.model_validate(product_service.update_product(db, product_id, data))
