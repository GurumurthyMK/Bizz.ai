"""CSV validation and transactional import for business data.

Two-phase workflow: preview validates without writing anything; import
re-validates and inserts all rows in a single transaction (all-or-nothing).
Row-level checks reuse the existing Create schemas, so import validation can
never drift from API validation. References use business keys
(customer email, product SKU, campaign name), never raw ids.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.campaign import Campaign
from app.models.customer import Customer
from app.models.import_job import ImportJob
from app.models.interaction import Interaction
from app.models.product import Product
from app.models.transaction import Transaction
from app.schemas.campaign import CampaignCreate
from app.schemas.customer import CustomerCreate
from app.schemas.interaction import InteractionCreate
from app.schemas.product import ProductCreate
from app.schemas.transaction import TransactionCreate

DataEntity = Literal["customers", "products", "transactions", "campaigns", "interactions"]
ENTITIES: tuple[DataEntity, ...] = (
    "customers",
    "products",
    "transactions",
    "campaigns",
    "interactions",
)

MAX_CSV_BYTES = 10 * 1024 * 1024
MAX_CSV_ROWS = 100_000
PREVIEW_ERROR_CAP = 50
PREVIEW_SAMPLE_ROWS = 10

ALLOWED_CONTENT_TYPES = frozenset(
    {"text/csv", "text/plain", "application/csv", "application/vnd.ms-excel", ""}
)


class CSVReadError(Exception):
    """File-level problem: wrong type, too large, undecodable, empty."""


async def read_upload_capped(file: Any) -> bytes:
    """Read an upload without ever buffering more than the cap plus one chunk.

    Prevents oversized bodies from exhausting server memory before the size
    check in ``read_csv_file`` can reject them.
    """
    chunks: list[bytes] = []
    received = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        received += len(chunk)
        if received > MAX_CSV_BYTES:
            raise CSVReadError(f"File too large: limit is {MAX_CSV_BYTES} bytes.")
        chunks.append(chunk)
    return b"".join(chunks)


class ValidationFailed(Exception):
    """Row-level validation failed; carries per-row errors, writes nothing."""

    def __init__(self, errors: list[RowError]) -> None:
        super().__init__(f"{len(errors)} invalid row(s)")
        self.errors = errors


@dataclass
class RowError:
    line: int
    column: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"line": self.line, "column": self.column, "message": self.message}


@dataclass
class ParsedFile:
    filename: str
    columns: list[str]
    rows: list[tuple[int, dict[str, str]]]


@dataclass
class ValidatedRow:
    line: int
    values: dict[str, Any]


@dataclass
class ValidationReport:
    entity: str
    filename: str
    columns: list[str]
    total_rows: int
    valid: list[ValidatedRow] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)


def sanitize_filename(filename: str | None) -> str:
    """Basename only, capped length. Never used for storage — audit trail only."""
    if not filename:
        return "upload.csv"
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip() or "upload.csv"
    return base[:255]


def read_csv_file(filename: str | None, content_type: str | None, raw: bytes) -> ParsedFile:
    name = sanitize_filename(filename)
    if not name.lower().endswith(".csv"):
        raise CSVReadError(f"Unsupported file type {name!r}: expected a .csv file.")
    if (content_type or "") not in ALLOWED_CONTENT_TYPES:
        raise CSVReadError(f"Unsupported content type {content_type!r} for CSV import.")
    if len(raw) > MAX_CSV_BYTES:
        raise CSVReadError(f"File too large ({len(raw)} bytes): limit is {MAX_CSV_BYTES} bytes.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CSVReadError("File is not valid UTF-8 text.") from None
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CSVReadError("Empty file: no header row found.")
    columns = [col.strip() for col in reader.fieldnames if col.strip()]
    rows: list[tuple[int, dict[str, str]]] = []
    for record in reader:
        if len(rows) >= MAX_CSV_ROWS:
            raise CSVReadError(f"Too many rows: limit is {MAX_CSV_ROWS}.")
        # Skip fully blank lines; keep the reader's physical line number.
        values = {
            (key.strip() if key else ""): (value.strip() if value else "")
            for key, value in record.items()
            if key
        }
        if not any(values.values()):
            continue
        rows.append((reader.line_num, values))
    if not rows:
        raise CSVReadError("Empty file: no data rows found.")
    return ParsedFile(filename=name, columns=columns, rows=rows)


def _blank(value: str) -> bool:
    return value.strip() == ""


def _parse_int(raw: str, column: str, line: int, errors: list[RowError]) -> int | None:
    try:
        return int(raw.strip())
    except ValueError:
        errors.append(RowError(line, column, f"{raw!r} is not a valid integer."))
        return None


def _parse_decimal(raw: str, column: str, line: int, errors: list[RowError]) -> Decimal | None:
    try:
        return Decimal(raw.strip())
    except InvalidOperation:
        errors.append(RowError(line, column, f"{raw!r} is not a valid number."))
        return None


def _parse_datetime(raw: str, column: str, line: int, errors: list[RowError]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        errors.append(RowError(line, column, f"{raw!r} is not a valid datetime (use ISO format)."))
        return None
    if parsed.tzinfo is None:
        from datetime import UTC

        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _schema_errors(line: int, error: ValidationError, errors: list[RowError]) -> None:
    for detail in error.errors():
        column = str(detail["loc"][0]) if detail["loc"] else "row"
        errors.append(RowError(line, column, detail["msg"]))


# Required columns per entity (business-key references, not raw ids).
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "customers": ["first_name", "last_name", "email"],
    "products": ["sku", "name", "category", "unit_price"],
    "transactions": ["customer_email", "product_sku", "quantity", "unit_price", "transaction_date"],
    "campaigns": ["name", "channel", "campaign_type"],
    "interactions": ["customer_email", "interaction_type", "channel", "occurred_at"],
}


def _check_columns(entity: str, columns: list[str]) -> list[RowError]:
    missing = [col for col in REQUIRED_COLUMNS[entity] if col not in columns]
    return [RowError(1, col, f"Missing required column {col!r}.") for col in missing]


def _resolve_maps(
    db: Session, rows: list[tuple[int, dict[str, str]]], entity: str
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Single-query id maps for every referenced business key in the file."""
    emails = {
        record["customer_email"].strip().lower()
        for _, record in rows
        if entity in ("transactions", "interactions") and record.get("customer_email", "").strip()
    }
    skus = {
        record["product_sku"].strip()
        for _, record in rows
        if entity == "transactions" and record.get("product_sku", "").strip()
    }
    names = {
        record["campaign_name"].strip()
        for _, record in rows
        if entity == "interactions" and record.get("campaign_name", "").strip()
    }
    email_ids = (
        {
            email: ident
            for email, ident in db.execute(
                select(Customer.email, Customer.id).where(Customer.email.in_(emails))
            ).all()
        }
        if emails
        else {}
    )
    # Emails are stored lowercase; match case-insensitively.
    email_ids = {email.lower(): ident for email, ident in email_ids.items()}
    sku_ids = (
        {
            sku: ident
            for sku, ident in db.execute(
                select(Product.sku, Product.id).where(Product.sku.in_(skus))
            ).all()
        }
        if skus
        else {}
    )
    campaign_ids = (
        {
            name: ident
            for name, ident in db.execute(
                select(Campaign.name, Campaign.id).where(Campaign.name.in_(names))
            ).all()
        }
        if names
        else {}
    )
    return email_ids, sku_ids, campaign_ids


def _validate_row(
    db: Session,
    entity: str,
    line: int,
    record: dict[str, str],
    maps: tuple[dict[str, int], dict[str, int], dict[str, int]],
    seen_skus: set[str],
    existing_skus: set[str],
) -> tuple[dict[str, Any] | None, list[RowError]]:
    email_ids, sku_ids, campaign_ids = maps
    errors: list[RowError] = []

    def required(column: str) -> str | None:
        value = record.get(column, "")
        if _blank(value):
            errors.append(RowError(line, column, "Required value is missing."))
            return None
        return value.strip()

    if entity == "customers":
        first = required("first_name")
        last = required("last_name")
        email = required("email")
        if errors:
            return None, errors
        assert first is not None and last is not None and email is not None
        try:
            CustomerCreate(
                first_name=first,
                last_name=last,
                email=email,
                phone=record.get("phone") or None,
                city=record.get("city") or None,
                country=record.get("country") or None,
            )
        except ValidationError as exc:
            _schema_errors(line, exc, errors)
            return None, errors
        return {
            "first_name": first,
            "last_name": last,
            "email": email.lower(),
            "phone": record.get("phone") or None,
            "city": record.get("city") or None,
            "country": record.get("country") or None,
        }, errors

    if entity == "products":
        sku = required("sku")
        name = required("name")
        category = required("category")
        price_raw = required("unit_price")
        if errors:
            return None, errors
        assert sku is not None and name is not None and category is not None
        assert price_raw is not None
        price = _parse_decimal(price_raw, "unit_price", line, errors)
        if price is None:
            return None, errors
        if sku in seen_skus:
            errors.append(RowError(line, "sku", f"Duplicate SKU {sku!r} within this file."))
            return None, errors
        if sku in existing_skus:
            errors.append(RowError(line, "sku", f"SKU {sku!r} already exists."))
            return None, errors
        seen_skus.add(sku)
        try:
            ProductCreate(
                sku=sku,
                name=name,
                category=category,
                brand=record.get("brand") or None,
                unit_price=price,
                currency=(record.get("currency") or "USD").upper(),
                is_active=(record.get("is_active") or "true").lower() != "false",
            )
        except ValidationError as exc:
            _schema_errors(line, exc, errors)
            return None, errors
        return {
            "sku": sku,
            "name": name,
            "category": category,
            "brand": record.get("brand") or None,
            "unit_price": price,
            "currency": (record.get("currency") or "USD").upper(),
            "is_active": (record.get("is_active") or "true").lower() != "false",
        }, errors

    if entity == "transactions":
        email = required("customer_email")
        sku = required("product_sku")
        qty_raw = required("quantity")
        price_raw = required("unit_price")
        date_raw = required("transaction_date")
        if errors:
            return None, errors
        assert email is not None and sku is not None
        assert qty_raw is not None and price_raw is not None and date_raw is not None
        quantity = _parse_int(qty_raw, "quantity", line, errors)
        price = _parse_decimal(price_raw, "unit_price", line, errors)
        occurred = _parse_datetime(date_raw, "transaction_date", line, errors)
        discount = Decimal("0")
        if record.get("discount", "").strip():
            parsed_discount = _parse_decimal(record["discount"], "discount", line, errors)
            if parsed_discount is None:
                return None, errors
            discount = parsed_discount
        customer_id = email_ids.get(email.lower())
        if customer_id is None:
            errors.append(RowError(line, "customer_email", f"Unknown customer {email!r}."))
        product_id = sku_ids.get(sku)
        if product_id is None:
            errors.append(RowError(line, "product_sku", f"Unknown product {sku!r}."))
        if errors or quantity is None or price is None or occurred is None:
            return None, errors
        assert customer_id is not None and product_id is not None
        try:
            TransactionCreate(
                customer_id=customer_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=price,
                discount=discount,
                status=record.get("status") or "completed",
                transaction_date=occurred,
            )
        except ValidationError as exc:
            _schema_errors(line, exc, errors)
            return None, errors
        return {
            "customer_id": customer_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": price,
            "discount": discount,
            # Same formula as the transaction service: qty * price - discount.
            "total_amount": quantity * price - discount,
            "status": record.get("status") or "completed",
            "transaction_date": occurred,
        }, errors

    if entity == "campaigns":
        name = required("name")
        channel = required("channel")
        kind = required("campaign_type")
        if errors:
            return None, errors
        assert name is not None and channel is not None and kind is not None
        start = end = None
        budget = None
        if record.get("start_date", "").strip():
            start = _parse_datetime(record["start_date"], "start_date", line, errors)
        if record.get("end_date", "").strip():
            end = _parse_datetime(record["end_date"], "end_date", line, errors)
        if record.get("budget", "").strip():
            budget = _parse_decimal(record["budget"], "budget", line, errors)
        if errors:
            return None, errors
        try:
            CampaignCreate(
                name=name,
                channel=channel,
                campaign_type=kind,
                status=record.get("status") or "draft",
                start_date=start,
                end_date=end,
                budget=budget,
                description=record.get("description") or None,
            )
        except ValidationError as exc:
            _schema_errors(line, exc, errors)
            return None, errors
        return {
            "name": name,
            "channel": channel,
            "campaign_type": kind,
            "status": record.get("status") or "draft",
            "start_date": start,
            "end_date": end,
            "budget": budget,
            "description": record.get("description") or None,
        }, errors

    # entity == "interactions"
    email = required("customer_email")
    itype = required("interaction_type")
    channel = required("channel")
    occurred_raw = required("occurred_at")
    if errors:
        return None, errors
    assert email is not None and itype is not None and channel is not None
    assert occurred_raw is not None
    occurred = _parse_datetime(occurred_raw, "occurred_at", line, errors)
    customer_id = email_ids.get(email.lower())
    if customer_id is None:
        errors.append(RowError(line, "customer_email", f"Unknown customer {email!r}."))
    campaign_id = None
    if record.get("campaign_name", "").strip():
        campaign_id = campaign_ids.get(record["campaign_name"].strip())
        if campaign_id is None:
            errors.append(
                RowError(
                    line, "campaign_name", f"Unknown campaign {record['campaign_name'].strip()!r}."
                )
            )
    if errors or occurred is None:
        return None, errors
    assert customer_id is not None
    try:
        InteractionCreate(
            customer_id=customer_id,
            campaign_id=campaign_id,
            interaction_type=itype,
            channel=channel,
            occurred_at=occurred,
            summary=record.get("summary") or None,
        )
    except ValidationError as exc:
        _schema_errors(line, exc, errors)
        return None, errors
    return {
        "customer_id": customer_id,
        "campaign_id": campaign_id,
        "interaction_type": itype,
        "channel": channel,
        "occurred_at": occurred,
        "summary": record.get("summary") or None,
    }, errors


def validate_parsed(db: Session, entity: str, parsed: ParsedFile) -> ValidationReport:
    report = ValidationReport(
        entity=entity, filename=parsed.filename, columns=parsed.columns, total_rows=len(parsed.rows)
    )
    column_errors = _check_columns(entity, parsed.columns)
    if column_errors:
        report.errors.extend(column_errors)
        return report
    maps = _resolve_maps(db, parsed.rows, entity)
    existing_skus: set[str] = set()
    if entity == "products":
        skus_in_file = [
            record["sku"].strip() for _, record in parsed.rows if record.get("sku", "").strip()
        ]
        existing_skus = {
            row[0]
            for row in db.execute(select(Product.sku).where(Product.sku.in_(skus_in_file))).all()
        }
    seen_skus: set[str] = set()
    for line, record in parsed.rows:
        values, row_errors = _validate_row(db, entity, line, record, maps, seen_skus, existing_skus)
        if row_errors:
            report.errors.extend(row_errors)
        else:
            assert values is not None
            report.valid.append(ValidatedRow(line=line, values=values))
    return report


def validate_upload(
    db: Session,
    entity: str,
    filename: str | None,
    content_type: str | None,
    raw: bytes,
) -> ValidationReport:
    parsed = read_csv_file(filename, content_type, raw)
    return validate_parsed(db, entity, parsed)


MODEL_BY_ENTITY = {
    "customers": Customer,
    "products": Product,
    "transactions": Transaction,
    "campaigns": Campaign,
    "interactions": Interaction,
}


def import_validated(db: Session, entity: str, report: ValidationReport) -> int:
    """Insert all validated rows in one transaction. Rolls back on any error."""
    model = MODEL_BY_ENTITY[entity]
    try:
        db.add_all([model(**row.values) for row in report.valid])
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValidationFailed(
            [RowError(0, "", f"Import rejected by database constraints: {exc.orig}")]
        ) from exc
    return len(report.valid)


def record_import_job(
    db: Session,
    entity: str,
    filename: str,
    report: ValidationReport,
    inserted: int,
    status: str,
) -> None:
    db.add(
        ImportJob(
            entity=entity,
            filename=filename,
            rows_total=report.total_rows,
            rows_valid=len(report.valid),
            rows_inserted=inserted,
            rows_failed=len(report.errors),
            status=status,
            error_summary=[error.to_dict() for error in report.errors[:PREVIEW_ERROR_CAP]]
            if report.errors
            else None,
        )
    )
    db.commit()
