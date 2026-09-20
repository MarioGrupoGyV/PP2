import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, PersistenceError, ResourceNotFoundError
from app.models.process_stage import ProcessStage
from app.repositories import process_stage_repository
from app.schemas.process_stage import ProcessStageCreate, ProcessStageUpdate

logger = logging.getLogger(__name__)


def list_process_stages(db: Session) -> list[ProcessStage]:
    return process_stage_repository.list_all(db)


def get_process_stage(db: Session, stage_id: UUID) -> ProcessStage:
    stage = process_stage_repository.get_by_id(db, stage_id)
    if stage is None:
        raise ResourceNotFoundError("Process stage not found")
    return stage


def create_process_stage(
    db: Session,
    data: ProcessStageCreate,
) -> ProcessStage:
    if process_stage_repository.get_by_code(db, data.code):
        raise ConflictError("Process stage code already exists")
    if process_stage_repository.get_by_sequence(db, data.sequence):
        raise ConflictError("Process stage sequence already exists")

    stage = ProcessStage(**data.model_dump())
    process_stage_repository.add(db, stage)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Process stage code or sequence already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Process stage persistence failed: %s", type(exc).__name__)
        raise PersistenceError("Unable to persist process stage") from exc

    db.refresh(stage)
    return stage


def update_process_stage(
    db: Session,
    stage_id: UUID,
    data: ProcessStageUpdate,
) -> ProcessStage:
    stage = get_process_stage(db, stage_id)
    changes = data.model_dump(exclude_unset=True)

    if "code" in changes:
        duplicate = process_stage_repository.get_by_code(db, changes["code"])
        if duplicate is not None and duplicate.id != stage.id:
            raise ConflictError("Process stage code already exists")
    if "sequence" in changes:
        duplicate = process_stage_repository.get_by_sequence(
            db,
            changes["sequence"],
        )
        if duplicate is not None and duplicate.id != stage.id:
            raise ConflictError("Process stage sequence already exists")

    for field, value in changes.items():
        setattr(stage, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Process stage code or sequence already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Process stage update failed: %s", type(exc).__name__)
        raise PersistenceError("Unable to update process stage") from exc

    db.refresh(stage)
    return stage
