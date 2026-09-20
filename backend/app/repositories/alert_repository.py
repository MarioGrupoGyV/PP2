from uuid import UUID

from sqlalchemy import Sequence, case, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.alert import Alert, AlertAction
from app.models.commercial_case import CommercialCase
from app.models.enums import AlertStatus, CaseStatus, RiskLevel
from app.models.event import Event
from app.models.prediction import Prediction

OPEN_STATUSES = (AlertStatus.ACTIVE, AlertStatus.ATTENDED)


def next_alert_code(db: Session) -> str:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        value = db.scalar(select(Sequence("alert_code_seq").next_value()))
    else:
        value = (db.scalar(select(func.count()).select_from(Alert)) or 0) + 1
    return f"ALR-{int(value):06d}"


def get_prediction(db: Session, prediction_id: UUID) -> Prediction | None:
    return db.scalar(
        select(Prediction)
        .options(joinedload(Prediction.model_run), joinedload(Prediction.commercial_case))
        .where(Prediction.id == prediction_id)
    )


def get_open_for_case(db: Session, case_id: UUID, *, lock: bool = False) -> Alert | None:
    statement = select(Alert).where(Alert.case_id == case_id, Alert.status.in_(OPEN_STATUSES))
    if lock:
        statement = statement.with_for_update(of=Alert)
    else:
        statement = statement.options(
            joinedload(Alert.commercial_case), joinedload(Alert.latest_prediction)
        )
    return db.scalar(statement)


def get_by_fingerprint(db: Session, fingerprint: str) -> Alert | None:
    return db.scalar(
        select(Alert)
        .options(joinedload(Alert.commercial_case), joinedload(Alert.latest_prediction))
        .where(Alert.fingerprint == fingerprint)
    )


def latest_closed_for_case(db: Session, case_id: UUID) -> Alert | None:
    return db.scalar(
        select(Alert)
        .options(joinedload(Alert.latest_prediction))
        .where(
            Alert.case_id == case_id,
            Alert.status.in_((AlertStatus.RESOLVED, AlertStatus.DISMISSED)),
        )
        .order_by(func.coalesce(Alert.resolved_at, Alert.dismissed_at).desc(), Alert.id.desc())
        .limit(1)
    )


def get_alert(db: Session, alert_id: UUID, *, lock: bool = False) -> Alert | None:
    statement = select(Alert).where(Alert.id == alert_id)
    if lock:
        statement = statement.with_for_update(of=Alert)
    else:
        statement = statement.options(
            joinedload(Alert.commercial_case),
            joinedload(Alert.origin_prediction).joinedload(Prediction.model_run),
            joinedload(Alert.latest_prediction).joinedload(Prediction.model_run),
        )
    return db.scalar(statement)


def list_alerts(
    db: Session,
    *,
    status: AlertStatus | None,
    risk_level: RiskLevel | None,
    case_code: str | None,
    min_risk_score: float | None,
    offset: int,
    limit: int,
) -> tuple[list[Alert], int]:
    filters = []
    if status is not None:
        filters.append(Alert.status == status)
    if risk_level is not None:
        filters.append(Alert.risk_level == risk_level)
    if case_code:
        filters.append(CommercialCase.case_code.ilike(f"%{case_code}%"))
    if min_risk_score is not None:
        filters.append(Alert.risk_score >= min_risk_score)
    base = select(Alert).join(CommercialCase).where(*filters)
    priority = case(
        (Alert.status == AlertStatus.ACTIVE, 0),
        (Alert.status == AlertStatus.ATTENDED, 1),
        else_=2,
    )
    items = list(
        db.scalars(
            base.options(joinedload(Alert.commercial_case))
            .order_by(priority, Alert.risk_score.desc(), Alert.triggered_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    total = db.scalar(select(func.count()).select_from(Alert).join(CommercialCase).where(*filters)) or 0
    return items, total


def list_for_case(db: Session, case_id: UUID) -> list[Alert]:
    return list(
        db.scalars(
            select(Alert)
            .options(joinedload(Alert.commercial_case))
            .where(Alert.case_id == case_id)
            .order_by(Alert.triggered_at, Alert.id)
        ).all()
    )


def list_actions(db: Session, alert_id: UUID) -> list[AlertAction]:
    return list(
        db.scalars(
            select(AlertAction)
            .where(AlertAction.alert_id == alert_id)
            .order_by(AlertAction.created_at, AlertAction.id)
        ).all()
    )


def candidate_case_ids(
    db: Session,
    *,
    as_of,
    requested_ids: list[UUID] | None,
    limit: int,
) -> list[UUID]:
    statement = select(CommercialCase.id)
    if requested_ids is not None:
        statement = statement.where(CommercialCase.id.in_(requested_ids))
    elif as_of is None:
        statement = statement.where(CommercialCase.status == CaseStatus.ACTIVE)
    statement = statement.order_by(CommercialCase.started_at, CommercialCase.id).limit(limit)
    return list(db.scalars(statement).all())


def has_observable_event(db: Session, case_id: UUID, as_of) -> bool:
    statement = select(Event.id).where(Event.case_id == case_id)
    if as_of is not None:
        statement = statement.where(Event.timestamp <= as_of)
    return db.scalar(statement.limit(1)) is not None


def summary(db: Session) -> dict:
    counts = {status: 0 for status in AlertStatus}
    for status, count in db.execute(
        select(Alert.status, func.count()).group_by(Alert.status)
    ).all():
        counts[status] = int(count)
    risk_counts = {level: 0 for level in RiskLevel}
    for level, count in db.execute(
        select(Alert.risk_level, func.count()).group_by(Alert.risk_level)
    ).all():
        risk_counts[level] = int(count)
    average = db.scalar(
        select(func.avg(Alert.risk_score)).where(Alert.status.in_(OPEN_STATUSES))
    )
    total = sum(counts.values())
    return {
        "total_alerts": total,
        "active": counts[AlertStatus.ACTIVE],
        "attended": counts[AlertStatus.ATTENDED],
        "resolved": counts[AlertStatus.RESOLVED],
        "dismissed": counts[AlertStatus.DISMISSED],
        "open_alerts": counts[AlertStatus.ACTIVE] + counts[AlertStatus.ATTENDED],
        "average_open_risk_score": round(float(average), 6) if average is not None else None,
        "by_risk_level": risk_counts,
    }
