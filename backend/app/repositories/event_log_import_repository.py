from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_log_import import EventLogImport


def add(db: Session, event_log_import: EventLogImport) -> EventLogImport:
    db.add(event_log_import)
    return event_log_import


def get_by_id(db: Session, import_id: UUID) -> EventLogImport | None:
    return db.get(EventLogImport, import_id)


def get_by_hash(db: Session, file_sha256: str) -> EventLogImport | None:
    statement = select(EventLogImport).where(
        EventLogImport.file_sha256 == file_sha256
    )
    return db.scalar(statement)


def list_recent(db: Session, *, limit: int) -> list[EventLogImport]:
    statement = (
        select(EventLogImport)
        .order_by(EventLogImport.created_at.desc(), EventLogImport.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
