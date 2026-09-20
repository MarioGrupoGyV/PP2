from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.process_stage import (
    ProcessStageCreate,
    ProcessStageRead,
    ProcessStageUpdate,
)
from app.services import process_stage_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ProcessStageRead])
def list_process_stages(db: DbSession) -> list[ProcessStageRead]:
    return process_stage_service.list_process_stages(db)


@router.get("/{stage_id}", response_model=ProcessStageRead)
def get_process_stage(stage_id: UUID, db: DbSession) -> ProcessStageRead:
    return process_stage_service.get_process_stage(db, stage_id)


@router.post(
    "",
    response_model=ProcessStageRead,
    status_code=status.HTTP_201_CREATED,
)
def create_process_stage(
    data: ProcessStageCreate,
    db: DbSession,
) -> ProcessStageRead:
    return process_stage_service.create_process_stage(db, data)


@router.patch("/{stage_id}", response_model=ProcessStageRead)
def update_process_stage(
    stage_id: UUID,
    data: ProcessStageUpdate,
    db: DbSession,
) -> ProcessStageRead:
    return process_stage_service.update_process_stage(db, stage_id, data)
