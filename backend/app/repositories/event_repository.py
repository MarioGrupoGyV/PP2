from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.event import Event


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
