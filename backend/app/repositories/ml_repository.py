from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models.commercial_case import CommercialCase
from app.models.enums import RiskLevel
from app.models.ml_model_run import MlModelRun
from app.models.prediction import Prediction


def get_active_model_run(db: Session) -> MlModelRun | None:
    return db.scalar(select(MlModelRun).where(MlModelRun.is_active.is_(True)))


def activate_model_run(db: Session, model_run: MlModelRun) -> None:
    db.execute(update(MlModelRun).where(MlModelRun.is_active.is_(True)).values(is_active=False))
    model_run.is_active = True
    db.add(model_run)


def get_prediction_by_fingerprint(db: Session, fingerprint: str) -> Prediction | None:
    return db.scalar(
        select(Prediction)
        .options(joinedload(Prediction.commercial_case), joinedload(Prediction.model_run))
        .where(Prediction.prediction_fingerprint == fingerprint)
    )


def add_prediction(db: Session, prediction: Prediction) -> None:
    db.add(prediction)


def latest_prediction_for_case(db: Session, case_id: UUID) -> Prediction | None:
    return db.scalar(
        select(Prediction)
        .options(joinedload(Prediction.commercial_case), joinedload(Prediction.model_run))
        .where(Prediction.case_id == case_id)
        .order_by(Prediction.predicted_at.desc(), Prediction.id.desc())
        .limit(1)
    )


def list_predictions(
    db: Session,
    *,
    risk_level: RiskLevel | None,
    case_code: str | None,
    predicted_label: bool | None,
    offset: int,
    limit: int,
) -> tuple[list[Prediction], int]:
    filters = []
    if risk_level is not None:
        filters.append(Prediction.risk_level == risk_level)
    if case_code:
        filters.append(CommercialCase.case_code.ilike(f"%{case_code}%"))
    if predicted_label is not None:
        filters.append(Prediction.predicted_label == predicted_label)
    base = select(Prediction).join(CommercialCase).where(*filters)
    items = list(
        db.scalars(
            base.options(
                joinedload(Prediction.commercial_case),
                joinedload(Prediction.model_run),
            )
            .order_by(Prediction.predicted_at.desc(), Prediction.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    total = db.scalar(
        select(func.count()).select_from(Prediction).join(CommercialCase).where(*filters)
    ) or 0
    return items, total
