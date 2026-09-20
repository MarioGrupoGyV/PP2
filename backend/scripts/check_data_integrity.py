"""Calcula una huella reproducible de los datos analíticos protegidos.

Metodología ``gyv-integrity-v1``:
- selecciona un conjunto fijo y documentado de columnas;
- ordena cada tabla por UUID ascendente;
- normaliza timestamps a UTC con seis decimales y sufijo ``Z``;
- serializa UUID, enums y JSON de forma canónica;
- alimenta SHA-256 con una línea JSON UTF-8 por fila.

Ejecutar desde ``backend`` con ``python -m scripts.check_data_integrity``.
"""

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.deviation import Deviation
from app.models.event import Event
from app.models.ml_model_run import MlModelRun

METHODOLOGY = "gyv-integrity-v1"

EVENT_COLUMNS = (
    "id", "case_id", "stage_id", "import_id", "source_row_number",
    "event_fingerprint", "activity", "event_type", "resource", "timestamp",
    "metadata_", "created_at",
)
DEVIATION_COLUMNS = (
    "id", "case_id", "event_id", "stage_id", "type", "severity",
    "description", "expected_value", "actual_value", "details", "fingerprint",
    "detected_at", "resolved_at", "created_at",
)


def _canonical(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, dict):
        return {str(key): _canonical(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    raise TypeError(f"Tipo no soportado por la serialización canónica: {type(value).__name__}")


def _hash_rows(rows: Iterable[Any], columns: tuple[str, ...]) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for row in rows:
        payload = {column: _canonical(getattr(row, column)) for column in columns}
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        count += 1
    return count, digest.hexdigest()


def calculate_integrity() -> dict[str, Any]:
    with SessionLocal() as db:
        events = db.scalars(select(Event).order_by(Event.id)).all()
        deviations = db.scalars(select(Deviation).order_by(Deviation.id)).all()
        event_count, event_sha256 = _hash_rows(events, EVENT_COLUMNS)
        deviation_count, deviation_sha256 = _hash_rows(deviations, DEVIATION_COLUMNS)
        active_model = db.scalar(select(MlModelRun).where(MlModelRun.is_active.is_(True)))
        if active_model is None:
            raise RuntimeError("No existe un modelo ML activo")
        return {
            "methodology": METHODOLOGY,
            "events": {"count": event_count, "sha256": event_sha256},
            "deviations": {"count": deviation_count, "sha256": deviation_sha256},
            "active_model": {
                "model_version": active_model.model_version,
                "artifact_sha256": active_model.artifact_sha256,
            },
        }


def main() -> None:
    print(json.dumps(calculate_integrity(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
