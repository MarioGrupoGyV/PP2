import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    PersistenceError,
    ResourceNotFoundError,
)
from app.models.commercial_case import CommercialCase
from app.repositories import commercial_case_repository, process_stage_repository
from app.schemas.commercial_case import CommercialCaseCreate

logger = logging.getLogger(__name__)


def list_commercial_cases(
    db: Session,
    *,
    page: int,
    page_size: int,
) -> tuple[list[CommercialCase], int]:
    offset = (page - 1) * page_size
    return commercial_case_repository.list_page(
        db,
        offset=offset,
        limit=page_size,
    )


def get_commercial_case(db: Session, case_id: UUID) -> CommercialCase:
    commercial_case = commercial_case_repository.get_by_id(db, case_id)
    if commercial_case is None:
        raise ResourceNotFoundError("Commercial case not found")
    return commercial_case


def get_commercial_case_by_code(
    db: Session,
    case_code: str,
) -> CommercialCase:
    commercial_case = commercial_case_repository.get_by_code(
        db,
        case_code.upper(),
    )
    if commercial_case is None:
        raise ResourceNotFoundError("Commercial case not found")
    return commercial_case


def create_commercial_case(
    db: Session,
    data: CommercialCaseCreate,
) -> CommercialCase:
    if commercial_case_repository.get_by_code(db, data.case_code):
        raise ConflictError("Commercial case code already exists")

    stage = process_stage_repository.get_by_id(db, data.current_stage_id)
    if stage is None:
        raise ResourceNotFoundError("Process stage not found")
    if not stage.active:
        raise DomainValidationError("Process stage is inactive")

    commercial_case = CommercialCase(**data.model_dump())
    commercial_case_repository.add(db, commercial_case)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Commercial case code already exists") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning("Commercial case persistence failed: %s", type(exc).__name__)
        raise PersistenceError("Unable to persist commercial case") from exc

    db.refresh(commercial_case)
    return commercial_case
