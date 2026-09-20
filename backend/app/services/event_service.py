import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DomainValidationError,
    PersistenceError,
    ResourceNotFoundError,
)
from app.models.enums import EventType
from app.models.event import Event
from app.repositories import (
    commercial_case_repository,
    event_repository,
    process_stage_repository,
)
from app.schemas.event import EventCreate

logger = logging.getLogger(__name__)


def create_event(
    db: Session,
    case_id: UUID,
    data: EventCreate,
) -> Event:
    commercial_case = commercial_case_repository.get_by_id(
        db,
        case_id,
        for_update=True,
    )
    if commercial_case is None:
        raise ResourceNotFoundError("Commercial case not found")

    stage = process_stage_repository.get_by_id(db, data.stage_id)
    if stage is None:
        raise ResourceNotFoundError("Process stage not found")
    if data.event_type == EventType.STAGE_CHANGE and not stage.active:
        raise DomainValidationError("Process stage is inactive")

    event = Event(
        case_id=commercial_case.id,
        stage_id=stage.id,
        activity=data.activity,
        event_type=data.event_type,
        resource=data.resource,
        timestamp=data.timestamp,
        metadata_=data.metadata,
    )
    event_repository.add(db, event)

    if data.event_type == EventType.STAGE_CHANGE:
        commercial_case.current_stage_id = stage.id

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Event transaction failed: %s", type(exc).__name__)
        raise PersistenceError("Unable to persist event") from exc

    db.refresh(event)
    return event


def list_case_events(db: Session, case_id: UUID) -> list[Event]:
    if commercial_case_repository.get_by_id(db, case_id) is None:
        raise ResourceNotFoundError("Commercial case not found")
    return event_repository.list_for_case(db, case_id)


def list_events(
    db: Session,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Event], int]:
    offset = (page - 1) * page_size
    return event_repository.list_page(db, offset=offset, limit=page_size)
