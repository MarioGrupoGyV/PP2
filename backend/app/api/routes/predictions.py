from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import RiskLevel
from app.schemas.prediction import (
    ActiveModelRead,
    ModelEvaluationRead,
    PredictionList,
    PredictionRead,
    PredictionRequest,
)
from app.services import prediction_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/cases/{case_id}/predict", response_model=PredictionRead)
def predict_case(
    case_id: UUID,
    db: DbSession,
    data: Annotated[PredictionRequest | None, Body()] = None,
) -> PredictionRead:
    return prediction_service.predict_case(db, case_id, data.as_of if data else None)


@router.get("/cases/{case_id}/prediction", response_model=PredictionRead)
def latest_prediction(case_id: UUID, db: DbSession) -> PredictionRead:
    return prediction_service.latest_prediction(db, case_id)


@router.get("/predictions", response_model=PredictionList)
def list_predictions(
    db: DbSession,
    risk_level: RiskLevel | None = None,
    case_code: str | None = None,
    predicted_label: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PredictionList:
    return prediction_service.list_predictions(
        db, risk_level=risk_level, case_code=case_code,
        predicted_label=predicted_label, page=page, page_size=page_size,
    )


@router.get("/ml/model", response_model=ActiveModelRead)
def get_active_model(db: DbSession) -> ActiveModelRead:
    return prediction_service.get_active_model(db)


@router.get("/ml/evaluation", response_model=ModelEvaluationRead)
def get_evaluation(db: DbSession) -> ModelEvaluationRead:
    return prediction_service.get_evaluation(db)
