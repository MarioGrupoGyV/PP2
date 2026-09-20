from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.process_stage import ProcessStage


def list_all(db: Session) -> list[ProcessStage]:
    statement = select(ProcessStage).order_by(ProcessStage.sequence)
    return list(db.scalars(statement).all())


def get_by_id(db: Session, stage_id: UUID) -> ProcessStage | None:
    return db.get(ProcessStage, stage_id)


def get_by_code(db: Session, code: str) -> ProcessStage | None:
    statement = select(ProcessStage).where(ProcessStage.code == code)
    return db.scalar(statement)


def get_by_sequence(db: Session, sequence: int) -> ProcessStage | None:
    statement = select(ProcessStage).where(ProcessStage.sequence == sequence)
    return db.scalar(statement)


def add(db: Session, stage: ProcessStage) -> ProcessStage:
    db.add(stage)
    return stage
