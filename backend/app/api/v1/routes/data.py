"""Data endpoints: CSV preview/import, import jobs, data health."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.import_job import ImportJob
from app.schemas.common import MAX_PAGE_SIZE, Page
from app.schemas.data import (
    DataEntity,
    DataHealthResponse,
    ImportJobResponse,
    ImportResultResponse,
    PreviewResponse,
    RowErrorResponse,
)
from app.services import data_health as health_service
from app.services.data_import import (
    PREVIEW_ERROR_CAP,
    PREVIEW_SAMPLE_ROWS,
    CSVReadError,
    ValidationFailed,
    import_validated,
    read_upload_capped,
    record_import_job,
    validate_upload,
)
from app.services.pagination import normalize_pagination, paginate

router = APIRouter(
    prefix="/data",
    tags=["data"],
    dependencies=[Depends(get_current_user)],
)


def _preview_payload(entity: str, filename: str, columns: list[str], report) -> PreviewResponse:  # type: ignore[no-untyped-def]
    return PreviewResponse(
        entity=entity,
        filename=filename,
        columns=columns,
        total_rows=report.total_rows,
        valid_rows=len(report.valid),
        invalid_rows=len(report.errors),
        errors=[RowErrorResponse(**error.to_dict()) for error in report.errors[:PREVIEW_ERROR_CAP]],
        errors_truncated=len(report.errors) > PREVIEW_ERROR_CAP,
        sample=[
            {key: str(value) for key, value in row.values.items()}
            for row in report.valid[:PREVIEW_SAMPLE_ROWS]
        ],
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_import(
    entity: DataEntity = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> PreviewResponse:
    try:
        raw = await read_upload_capped(file)
        report = validate_upload(db, entity, file.filename, file.content_type, raw)
    except CSVReadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _preview_payload(entity, report.filename, report.columns, report)


@router.post("/import", response_model=ImportResultResponse)
async def import_csv(
    entity: DataEntity = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ImportResultResponse:
    try:
        raw = await read_upload_capped(file)
        report = validate_upload(db, entity, file.filename, file.content_type, raw)
    except CSVReadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if report.errors:
        record_import_job(db, entity, report.filename, report, 0, "failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[error.to_dict() for error in report.errors[:PREVIEW_ERROR_CAP]],
        )
    try:
        inserted = import_validated(db, entity, report)
    except ValidationFailed as exc:
        record_import_job(db, entity, report.filename, report, 0, "failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[error.to_dict() for error in exc.errors[:PREVIEW_ERROR_CAP]],
        ) from exc
    record_import_job(db, entity, report.filename, report, inserted, "completed")
    return ImportResultResponse(
        entity=entity,
        filename=report.filename,
        status="completed",
        rows_total=report.total_rows,
        rows_inserted=inserted,
        rows_failed=0,
        errors=[],
    )


@router.get("/health", response_model=DataHealthResponse)
def data_health(db: Session = Depends(get_db)) -> DataHealthResponse:
    return DataHealthResponse(**health_service.get_data_health(db))


@router.get("/imports", response_model=Page[ImportJobResponse])
def list_imports(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_PAGE_SIZE),
) -> Page[ImportJobResponse]:
    page, page_size = normalize_pagination(page, page_size, MAX_PAGE_SIZE)
    items, total = paginate(select(ImportJob).order_by(ImportJob.id.desc()), db, page, page_size)
    return Page[ImportJobResponse](
        items=[ImportJobResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
