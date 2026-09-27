from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.deviation import Deviation
from app.models.enums import DeviationSeverity, DeviationType


LOAD_OPTIONS = (
    joinedload(Deviation.commercial_case),
    joinedload(Deviation.stage),
)


def existing_fingerprints(db: Session, fingerprints: set[str]) -> set[str]:
    if not fingerprints:
        return set()
    found: set[str] = set()
    values = sorted(fingerprints)
    for start in range(0, len(values), 500):
        statement = select(Deviation.fingerprint).where(
            Deviation.fingerprint.in_(values[start : start + 500])
        )
        found.update(db.scalars(statement).all())
    return found


def add_all(db: Session, deviations: list[Deviation]) -> None:
    db.add_all(deviations)


def get_by_id(db: Session, deviation_id: UUID) -> Deviation | None:
    return db.scalar(
        select(Deviation)
        .options(*LOAD_OPTIONS)
        .where(Deviation.id == deviation_id)
    )


def list_filtered(
    db: Session,
    *,
    deviation_type: DeviationType | None = None,
    severity: DeviationSeverity | None = None,
    case_code: str | None = None,
    case_id: UUID | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Deviation], int]:
    from app.models.commercial_case import CommercialCase

    filters = []
    if deviation_type is not None:
        filters.append(Deviation.type == deviation_type)
    if severity is not None:
        filters.append(Deviation.severity == severity)
    if case_code:
        filters.append(CommercialCase.case_code.ilike(f"%{case_code}%"))
    if case_id is not None:
        filters.append(Deviation.case_id == case_id)
    base = select(Deviation).join(CommercialCase).where(*filters)
    items = list(
        db.scalars(
            base.options(*LOAD_OPTIONS)
            .order_by(Deviation.detected_at.desc(), Deviation.id)
            .offset(offset)
            .limit(limit)
        ).all()
    )
    total = db.scalar(
        select(func.count()).select_from(Deviation).join(CommercialCase).where(*filters)
    ) or 0
    return items, total


def all_for_case(db: Session, case_id: UUID) -> list[Deviation]:
    return list(
        db.scalars(
            select(Deviation)
            .options(*LOAD_OPTIONS)
            .where(Deviation.case_id == case_id)
            .order_by(Deviation.detected_at, Deviation.id)
        ).all()
    )


def summary(db: Session) -> tuple[int, int, dict[str, int], dict[str, int]]:
    total = db.scalar(select(func.count()).select_from(Deviation)) or 0
    affected_cases = db.scalar(select(func.count(func.distinct(Deviation.case_id)))) or 0
    type_rows = db.execute(
        select(Deviation.type, func.count()).group_by(Deviation.type)
    ).all()
    severity_rows = db.execute(
        select(Deviation.severity, func.count()).group_by(Deviation.severity)
    ).all()
    return (
        total,
        affected_cases,
        {item.value: count for item, count in type_rows},
        {item.value: count for item, count in severity_rows},
    )


def affected_case_counts_by_type(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Deviation.type, func.count(func.distinct(Deviation.case_id))).group_by(
            Deviation.type
        )
    ).all()
    return {item.value: count for item, count in rows}
