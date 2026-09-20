from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.enums import EventType
from app.models.commercial_case import CommercialCase
from app.models.process_stage import ProcessStage


def list_for_case(db: Session, case_id: UUID) -> list[Event]:
    statement = (
        select(Event)
        .where(Event.case_id == case_id)
        .order_by(Event.timestamp, Event.created_at, Event.id)
    )
    return list(db.scalars(statement).all())


def list_page(
    db: Session,
    *,
    offset: int,
    limit: int,
) -> tuple[list[Event], int]:
    statement = (
        select(Event)
        .order_by(Event.timestamp, Event.created_at, Event.id)
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(statement).all())
    total = db.scalar(select(func.count()).select_from(Event)) or 0
    return items, total


def add(db: Session, event: Event) -> Event:
    db.add(event)
    return event


def get_existing_fingerprints(
    db: Session,
    fingerprints: set[str],
) -> set[str]:
    if not fingerprints:
        return set()

    existing: set[str] = set()
    ordered = list(fingerprints)
    for start in range(0, len(ordered), 500):
        chunk = ordered[start : start + 500]
        statement = select(Event.event_fingerprint).where(
            Event.event_fingerprint.in_(chunk)
        )
        existing.update(db.scalars(statement).all())
    return existing


def get_latest_stage_change(db: Session, case_id: UUID) -> Event | None:
    statement = (
        select(Event)
        .where(
            Event.case_id == case_id,
            Event.event_type == EventType.STAGE_CHANGE,
        )
        .order_by(Event.timestamp.desc(), Event.created_at.desc(), Event.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def list_normalized(db: Session) -> list[dict[str, object]]:
    statement = (
        select(
            CommercialCase.case_code.label("case_code"),
            ProcessStage.code.label("stage_code"),
            Event.activity,
            Event.timestamp,
            Event.resource,
            Event.event_type,
        )
        .join(CommercialCase, CommercialCase.id == Event.case_id)
        .join(ProcessStage, ProcessStage.id == Event.stage_id)
        .order_by(CommercialCase.case_code, Event.timestamp, Event.id)
    )
    return [dict(row._mapping) for row in db.execute(statement).all()]
