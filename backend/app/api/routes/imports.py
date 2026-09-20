from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.imports import (
    EventLogImportRead,
    ImportPreview,
    ImportResult,
)
from app.services import csv_import_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CsvUpload = Annotated[UploadFile, File(description="Archivo Event Log en CSV")]


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    content = await file.read(csv_import_service.MAX_FILE_SIZE + 1)
    return file.filename or "event_log.csv", content


@router.post("/preview", response_model=ImportPreview)
async def preview_import(file: CsvUpload, db: DbSession) -> ImportPreview:
    filename, content = await _read_upload(file)
    return csv_import_service.preview_csv(
        db,
        filename=filename,
        content=content,
    )


@router.post(
    "/commit",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
)
async def commit_import(file: CsvUpload, db: DbSession) -> ImportResult:
    filename, content = await _read_upload(file)
    return csv_import_service.commit_csv(
        db,
        filename=filename,
        content=content,
    )


@router.get("/template")
def download_template() -> Response:
    return Response(
        content=csv_import_service.build_csv_template(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="event_log_template.csv"'
        },
    )


@router.get("", response_model=list[EventLogImportRead])
def list_imports(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[EventLogImportRead]:
    return csv_import_service.list_imports(db, limit=limit)


@router.get("/{import_id}", response_model=EventLogImportRead)
def get_import(import_id: UUID, db: DbSession) -> EventLogImportRead:
    return csv_import_service.get_import(db, import_id)
