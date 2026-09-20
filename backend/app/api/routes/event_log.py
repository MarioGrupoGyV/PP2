from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.imports import EventLogEntry
from app.services import csv_import_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[EventLogEntry])
def get_event_log(db: DbSession) -> list[EventLogEntry]:
    return csv_import_service.get_normalized_event_log(db)
