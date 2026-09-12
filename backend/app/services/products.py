"""Product business logic."""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.common import MAX_PAGE_SIZE
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.errors import ConflictError, NotFoundError
from app.services.pagination import normalize_pagination, paginate


def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(
        sku=data.sku.strip(),
        name=data.name.strip(),
        category=data.category.strip(),
        brand=data.brand,
        unit_price=data.unit_price,
        currency=data.currency.upper(),
        is_active=data.is_active,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"Product with sku '{product.sku}' already exists.") from None
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product", product_id)
    return product


def list_products(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    search: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[Product], int]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    stmt = select(Product).order_by(Product.id)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
    if category:
        stmt = stmt.where(Product.category == category)
    if brand:
        stmt = stmt.where(Product.brand == brand)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
    return paginate(stmt, db, page, page_size)


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    for field in ("name", "category"):
        if changes.get(field) is not None:
            changes[field] = changes[field].strip()
    if changes.get("currency") is not None:
        changes["currency"] = changes["currency"].upper()
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product
