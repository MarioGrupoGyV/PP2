from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import EventType


class ImportValidationError(BaseModel):
    row: int
    field: str
    message: str


class ImportPreviewRow(BaseModel):
    row: int
    case_code: str
    stage_code: str
    activity: str
    timestamp: datetime
    resource: str | None
    event_type: EventType
    source: str | None


class ImportPreview(BaseModel):
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    can_import: bool
    preview: list[ImportPreviewRow]
    errors: list[ImportValidationError]


class ImportResult(BaseModel):
    import_id: UUID
    filename: str
    total_rows: int
    cases_created: int
    cases_existing: int
    events_imported: int
    duplicates_skipped: int


class EventLogImportRead(BaseModel):
    id: UUID
    filename: str
    file_sha256: str
    total_rows: int
    imported_cases: int
    imported_events: int
    skipped_duplicates: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventLogEntry(BaseModel):
    case_code: str
    stage_code: str
    activity: str
    timestamp: datetime
    resource: str | None
    event_type: EventType
