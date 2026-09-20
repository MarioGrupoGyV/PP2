from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commercial_case import CommercialCase


def list_page(
    db: Session,
    *,
    offset: int,
    limit: int,
) -> tuple[list[CommercialCase], int]:
    statement = (
        select(CommercialCase)
        .order_by(CommercialCase.created_at.desc(), CommercialCase.id)
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(statement).all())
    total = db.scalar(select(func.count()).select_from(CommercialCase)) or 0
    return items, total


def get_by_id(
    db: Session,
    case_id: UUID,
    *,
    for_update: bool = False,
) -> CommercialCase | None:
    statement = select(CommercialCase).where(CommercialCase.id == case_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_by_code(db: Session, case_code: str) -> CommercialCase | None:
    statement = select(CommercialCase).where(
        CommercialCase.case_code == case_code
    )
    return db.scalar(statement)


def add(db: Session, commercial_case: CommercialCase) -> CommercialCase:
    db.add(commercial_case)
    return commercial_case
