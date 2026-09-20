import csv
import hashlib
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Final
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    FileTooLargeError,
    PersistenceError,
    ResourceNotFoundError,
)
from app.models.commercial_case import CommercialCase
from app.models.enums import CaseStatus, EventType
from app.models.event import Event
from app.models.event_log_import import EventLogImport
from app.repositories import (
    commercial_case_repository,
    event_log_import_repository,
    event_repository,
    process_stage_repository,
)
from app.schemas.imports import (
    EventLogEntry,
    ImportPreview,
    ImportPreviewRow,
    ImportResult,
    ImportValidationError,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE: Final = 10 * 1024 * 1024
PREVIEW_LIMIT: Final = 20
REQUIRED_COLUMNS: Final = {"case_code", "stage_code", "activity", "timestamp"}
TEMPLATE_COLUMNS: Final = [
    "case_code",
    "stage_code",
    "activity",
    "timestamp",
    "resource",
    "event_type",
    "source",
    "metadata",
]


@dataclass(frozen=True, slots=True)
class NormalizedImportRow:
    row_number: int
    case_code: str
    stage_code: str
    stage_id: UUID
    activity: str
    timestamp: datetime
    resource: str | None
    event_type: EventType
    source: str | None
    metadata: dict[str, Any]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ParsedImport:
    filename: str
    file_sha256: str
    total_rows: int
    rows: list[NormalizedImportRow]
    errors: list[ImportValidationError]
    duplicate_rows: int

    @property
    def invalid_rows(self) -> int:
        if any(error.row == 1 for error in self.errors):
            return self.total_rows
        return len({error.row for error in self.errors})

    @property
    def can_import(self) -> bool:
        return (
            self.total_rows > 0
            and not self.errors
            and len(self.rows) == self.total_rows
        )


def _safe_filename(filename: str) -> str:
    normalized = filename.replace("\\", "/")
    return PurePosixPath(normalized).name[:255] or "event_log.csv"


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _event_fingerprint(
    *,
    case_code: str,
    stage_code: str,
    activity: str,
    timestamp: datetime,
    event_type: EventType,
    resource: str | None,
    source: str | None,
    metadata: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "case_code": case_code,
            "stage_code": stage_code,
            "activity": activity,
            "timestamp": timestamp.isoformat(),
            "event_type": event_type.value,
            "resource": resource or "",
            "source": source or "",
            "metadata": metadata,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read_records(text: str) -> tuple[list[str], list[tuple[int, list[str]]]]:
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        raw_headers = next(reader)
    except StopIteration:
        return [], []
    except csv.Error as exc:
        raise DomainValidationError("El contenido no es un CSV válido") from exc

    headers = [header.strip().lower() for header in raw_headers]
    records: list[tuple[int, list[str]]] = []
    while True:
        row_number = reader.line_num + 1
        try:
            values = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            raise DomainValidationError(
                f"CSV inválido cerca de la fila {row_number}"
            ) from exc
        records.append((row_number, values))
    return headers, records


def validate_csv(
    db: Session,
    *,
    filename: str,
    content: bytes,
) -> ParsedImport:
    safe_filename = _safe_filename(filename)
    if not safe_filename.lower().endswith(".csv"):
        raise DomainValidationError("Solo se permiten archivos con extensión CSV")
    if len(content) > MAX_FILE_SIZE:
        raise FileTooLargeError("El archivo supera el límite de 10 MB")
    if not content:
        raise DomainValidationError("El archivo CSV está vacío")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DomainValidationError(
            "El archivo debe usar encoding UTF-8 o UTF-8-SIG"
        ) from exc
    if not text.strip():
        raise DomainValidationError("El archivo CSV está vacío")

    headers, records = _read_records(text)
    file_sha256 = hashlib.sha256(content).hexdigest()
    errors: list[ImportValidationError] = []

    if not headers or all(not header for header in headers):
        errors.append(
            ImportValidationError(
                row=1,
                field="file",
                message="El archivo no contiene una cabecera CSV válida.",
            )
        )
    if len(headers) != len(set(headers)):
        errors.append(
            ImportValidationError(
                row=1,
                field="columns",
                message="La cabecera contiene columnas duplicadas.",
            )
        )
    missing_columns = sorted(REQUIRED_COLUMNS - set(headers))
    if missing_columns:
        errors.append(
            ImportValidationError(
                row=1,
                field="columns",
                message=(
                    "Faltan columnas obligatorias: " + ", ".join(missing_columns)
                ),
            )
        )
    if not records:
        errors.append(
            ImportValidationError(
                row=1,
                field="file",
                message="El archivo no contiene filas de datos.",
            )
        )

    if errors:
        return ParsedImport(
            filename=safe_filename,
            file_sha256=file_sha256,
            total_rows=len(records),
            rows=[],
            errors=errors,
            duplicate_rows=0,
        )

    stages = {
        stage.code.upper(): stage
        for stage in process_stage_repository.list_all(db)
    }
    normalized_rows: list[NormalizedImportRow] = []
    seen_fingerprints: set[str] = set()
    duplicate_rows = 0

    for row_number, values in records:
        row_errors: list[ImportValidationError] = []
        if not values or all(not value.strip() for value in values):
            errors.append(
                ImportValidationError(
                    row=row_number,
                    field="row",
                    message="La fila está completamente vacía.",
                )
            )
            continue
        if len(values) > len(headers):
            errors.append(
                ImportValidationError(
                    row=row_number,
                    field="row",
                    message="La fila contiene más valores que la cabecera.",
                )
            )
            continue

        raw = {
            header: (values[index].strip() if index < len(values) else "")
            for index, header in enumerate(headers)
        }
        case_code = raw["case_code"].upper()
        stage_code = raw["stage_code"].upper()
        activity = raw["activity"]

        for field, value in (
            ("case_code", case_code),
            ("stage_code", stage_code),
            ("activity", activity),
            ("timestamp", raw["timestamp"]),
        ):
            if not value:
                row_errors.append(
                    ImportValidationError(
                        row=row_number,
                        field=field,
                        message=f"El campo {field} es obligatorio.",
                    )
                )

        stage = stages.get(stage_code)
        if stage_code and stage is None:
            row_errors.append(
                ImportValidationError(
                    row=row_number,
                    field="stage_code",
                    message=f"La etapa {stage_code} no existe.",
                )
            )
        elif stage is not None and not stage.active:
            row_errors.append(
                ImportValidationError(
                    row=row_number,
                    field="stage_code",
                    message=f"La etapa {stage_code} está inactiva.",
                )
            )

        timestamp: datetime | None = None
        if raw["timestamp"]:
            try:
                timestamp = _parse_timestamp(raw["timestamp"])
            except ValueError:
                row_errors.append(
                    ImportValidationError(
                        row=row_number,
                        field="timestamp",
                        message="El timestamp no es un ISO 8601 válido.",
                    )
                )

        event_type_value = (raw.get("event_type") or "STAGE_CHANGE").upper()
        try:
            event_type = EventType(event_type_value)
        except ValueError:
            event_type = EventType.STAGE_CHANGE
            row_errors.append(
                ImportValidationError(
                    row=row_number,
                    field="event_type",
                    message=f"El event_type {event_type_value} no es válido.",
                )
            )

        metadata: dict[str, Any] = {}
        metadata_value = raw.get("metadata") or "{}"
        try:
            parsed_metadata = json.loads(metadata_value)
            if not isinstance(parsed_metadata, dict):
                raise ValueError
            metadata = parsed_metadata
        except (json.JSONDecodeError, ValueError):
            row_errors.append(
                ImportValidationError(
                    row=row_number,
                    field="metadata",
                    message="metadata debe ser un objeto JSON válido.",
                )
            )

        errors.extend(row_errors)
        if row_errors or stage is None or timestamp is None:
            continue

        resource = raw.get("resource") or None
        source = raw.get("source") or None
        fingerprint = _event_fingerprint(
            case_code=case_code,
            stage_code=stage_code,
            activity=activity,
            timestamp=timestamp,
            event_type=event_type,
            resource=resource,
            source=source,
            metadata=metadata,
        )
        if fingerprint in seen_fingerprints:
            duplicate_rows += 1
            errors.append(
                ImportValidationError(
                    row=row_number,
                    field="row",
                    message="La fila está duplicada dentro del archivo.",
                )
            )
            continue
        seen_fingerprints.add(fingerprint)

        normalized_rows.append(
            NormalizedImportRow(
                row_number=row_number,
                case_code=case_code,
                stage_code=stage_code,
                stage_id=stage.id,
                activity=activity,
                timestamp=timestamp,
                resource=resource,
                event_type=event_type,
                source=source,
                metadata=metadata,
                fingerprint=fingerprint,
            )
        )

    return ParsedImport(
        filename=safe_filename,
        file_sha256=file_sha256,
        total_rows=len(records),
        rows=normalized_rows,
        errors=errors,
        duplicate_rows=duplicate_rows,
    )


def preview_csv(db: Session, *, filename: str, content: bytes) -> ImportPreview:
    parsed = validate_csv(db, filename=filename, content=content)
    preview = [
        ImportPreviewRow(
            row=row.row_number,
            case_code=row.case_code,
            stage_code=row.stage_code,
            activity=row.activity,
            timestamp=row.timestamp,
            resource=row.resource,
            event_type=row.event_type,
            source=row.source,
        )
        for row in parsed.rows[:PREVIEW_LIMIT]
    ]
    return ImportPreview(
        filename=parsed.filename,
        total_rows=parsed.total_rows,
        valid_rows=len(parsed.rows),
        invalid_rows=parsed.invalid_rows,
        duplicate_rows=parsed.duplicate_rows,
        can_import=parsed.can_import,
        preview=preview,
        errors=parsed.errors,
    )


def _first_value(
    rows: list[NormalizedImportRow],
    field: str,
) -> str | None:
    for row in sorted(rows, key=lambda item: (item.timestamp, item.row_number)):
        value = getattr(row, field)
        if value:
            return value
    return None


def commit_csv(db: Session, *, filename: str, content: bytes) -> ImportResult:
    parsed = validate_csv(db, filename=filename, content=content)
    if not parsed.can_import:
        raise DomainValidationError(
            "El archivo contiene errores y no puede importarse parcialmente"
        )
    if event_log_import_repository.get_by_hash(db, parsed.file_sha256):
        raise ConflictError("Este archivo ya fue importado anteriormente.")

    case_codes = {row.case_code for row in parsed.rows}
    cases_by_code = commercial_case_repository.get_by_codes(db, case_codes)
    existing_case_codes = set(cases_by_code)
    existing_fingerprints = event_repository.get_existing_fingerprints(
        db,
        {row.fingerprint for row in parsed.rows},
    )
    new_rows = [
        row for row in parsed.rows if row.fingerprint not in existing_fingerprints
    ]
    rows_by_case: dict[str, list[NormalizedImportRow]] = {}
    for row in new_rows:
        rows_by_case.setdefault(row.case_code, []).append(row)

    event_log_import = EventLogImport(
        filename=parsed.filename,
        file_sha256=parsed.file_sha256,
        total_rows=parsed.total_rows,
        imported_cases=0,
        imported_events=0,
        skipped_duplicates=len(existing_fingerprints),
    )
    event_log_import_repository.add(db, event_log_import)
    cases_created = 0

    try:
        db.flush()

        for case_code, case_rows in rows_by_case.items():
            if case_code in cases_by_code:
                continue
            ordered_rows = sorted(
                case_rows,
                key=lambda item: (item.timestamp, item.row_number),
            )
            stage_changes = [
                row
                for row in ordered_rows
                if row.event_type == EventType.STAGE_CHANGE
            ]
            current_row = stage_changes[-1] if stage_changes else ordered_rows[-1]
            commercial_case = CommercialCase(
                case_code=case_code,
                current_stage_id=current_row.stage_id,
                assigned_resource=_first_value(ordered_rows, "resource"),
                source=_first_value(ordered_rows, "source"),
                status=CaseStatus.ACTIVE,
                started_at=ordered_rows[0].timestamp,
            )
            commercial_case_repository.add(db, commercial_case)
            cases_by_code[case_code] = commercial_case
            cases_created += 1

        db.flush()

        touched_case_ids: set[UUID] = set()
        for row in new_rows:
            commercial_case = cases_by_code[row.case_code]
            event_repository.add(
                db,
                Event(
                    case_id=commercial_case.id,
                    stage_id=row.stage_id,
                    import_id=event_log_import.id,
                    source_row_number=row.row_number,
                    event_fingerprint=row.fingerprint,
                    activity=row.activity,
                    event_type=row.event_type,
                    resource=row.resource,
                    timestamp=row.timestamp,
                    metadata_=row.metadata,
                ),
            )
            touched_case_ids.add(commercial_case.id)

        db.flush()
        for case_id in touched_case_ids:
            latest_stage_change = event_repository.get_latest_stage_change(db, case_id)
            if latest_stage_change is not None:
                commercial_case = commercial_case_repository.get_by_id(db, case_id)
                if commercial_case is not None:
                    commercial_case.current_stage_id = latest_stage_change.stage_id

        event_log_import.imported_cases = cases_created
        event_log_import.imported_events = len(new_rows)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "La importación entra en conflicto con datos ya registrados"
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.warning("CSV import transaction failed: %s", type(exc).__name__)
        raise PersistenceError("No fue posible completar la importación") from exc

    db.refresh(event_log_import)
    return ImportResult(
        import_id=event_log_import.id,
        filename=event_log_import.filename,
        total_rows=event_log_import.total_rows,
        cases_created=cases_created,
        cases_existing=len(existing_case_codes),
        events_imported=len(new_rows),
        duplicates_skipped=len(existing_fingerprints),
    )


def list_imports(db: Session, *, limit: int) -> list[EventLogImport]:
    return event_log_import_repository.list_recent(db, limit=limit)


def get_import(db: Session, import_id: UUID) -> EventLogImport:
    event_log_import = event_log_import_repository.get_by_id(db, import_id)
    if event_log_import is None:
        raise ResourceNotFoundError("Importación no encontrada")
    return event_log_import


def get_normalized_event_log(db: Session) -> list[EventLogEntry]:
    return [
        EventLogEntry.model_validate(item)
        for item in event_repository.list_normalized(db)
    ]


def build_csv_template() -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=TEMPLATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(
        [
            {
                "case_code": "CASE-001",
                "stage_code": "LEAD",
                "activity": "Lead creado",
                "timestamp": "2026-09-01T09:00:00-05:00",
                "resource": "Asesor 01",
                "event_type": "STAGE_CHANGE",
                "source": "META_ADS",
                "metadata": "{}",
            },
            {
                "case_code": "CASE-001",
                "stage_code": "CONTACTED",
                "activity": "Lead contactado",
                "timestamp": "2026-09-01T09:15:00-05:00",
                "resource": "Asesor 01",
                "event_type": "STAGE_CHANGE",
                "source": "META_ADS",
                "metadata": json.dumps(
                    {"channel": "whatsapp"},
                    ensure_ascii=False,
                ),
            },
        ]
    )
    return output.getvalue().encode("utf-8")
