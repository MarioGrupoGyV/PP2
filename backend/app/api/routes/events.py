from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.event import EventCreate, EventList, EventRead
from app.services import event_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/cases/{case_id}/events",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    case_id: UUID,
    data: EventCreate,
    db: DbSession,
) -> EventRead:
    return event_service.create_event(db, case_id, data)


@router.get(
    "/cases/{case_id}/events",
    response_model=list[EventRead],
)
def list_case_events(case_id: UUID, db: DbSession) -> list[EventRead]:
    return event_service.list_case_events(db, case_id)


@router.get("/events", response_model=EventList)
def list_events(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> EventList:
    items, total = event_service.list_events(
        db,
        page=page,
        page_size=page_size,
    )
    return EventList(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )
