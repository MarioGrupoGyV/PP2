from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import AlertStatus, RiskLevel
from app.schemas.alert import (
    AlertActionRead,
    AlertActionRequest,
    AlertBatchRead,
    AlertDetail,
    AlertDismissRequest,
    AlertEvaluationRead,
    AlertEvaluationRequest,
    AlertList,
    AlertRead,
    AlertSummary,
    AlertTransitionRequest,
)
from app.services import alert_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/cases/{case_id}/alerts/evaluate", response_model=AlertEvaluationRead)
def evaluate_case_alert(
    case_id: UUID,
    db: DbSession,
    data: Annotated[AlertEvaluationRequest | None, Body()] = None,
) -> AlertEvaluationRead:
    return alert_service.evaluate_case(db, case_id, data.as_of if data else None)


@router.post("/alerts/evaluate", response_model=AlertBatchRead)
def evaluate_alerts(
    db: DbSession,
    data: Annotated[AlertEvaluationRequest | None, Body()] = None,
) -> AlertBatchRead:
    request = data or AlertEvaluationRequest()
    return alert_service.evaluate_batch(
        db,
        as_of=request.as_of,
        case_id=request.case_id,
        case_ids=request.case_ids,
        limit=request.limit,
    )


@router.get("/alerts/summary", response_model=AlertSummary)
def get_alert_summary(db: DbSession) -> AlertSummary:
    return alert_service.get_summary(db)


@router.get("/alerts", response_model=AlertList)
def list_alerts(
    db: DbSession,
    status_filter: Annotated[AlertStatus | None, Query(alias="status")] = None,
    risk_level: RiskLevel | None = None,
    case_code: str | None = None,
    min_risk_score: Annotated[float | None, Query(ge=0, le=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AlertList:
    return alert_service.list_alerts(
        db,
        status=status_filter,
        risk_level=risk_level,
        case_code=case_code,
        min_risk_score=min_risk_score,
        page=page,
        page_size=page_size,
    )


@router.get("/cases/{case_id}/alerts", response_model=list[AlertRead])
def alerts_for_case(case_id: UUID, db: DbSession) -> list[AlertRead]:
    return alert_service.alerts_for_case(db, case_id)


@router.get("/alerts/{alert_id}/actions", response_model=list[AlertActionRead])
def alert_actions(alert_id: UUID, db: DbSession) -> list[AlertActionRead]:
    return alert_service.actions_for_alert(db, alert_id)


@router.post(
    "/alerts/{alert_id}/actions",
    response_model=AlertActionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_alert_note(alert_id: UUID, data: AlertActionRequest, db: DbSession) -> AlertActionRead:
    return alert_service.add_note(db, alert_id, actor=data.actor, notes=data.notes)


@router.post("/alerts/{alert_id}/attend", response_model=AlertDetail)
def attend_alert(alert_id: UUID, data: AlertTransitionRequest, db: DbSession) -> AlertDetail:
    return alert_service.attend(db, alert_id, actor=data.actor, notes=data.notes)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertDetail)
def resolve_alert(alert_id: UUID, data: AlertTransitionRequest, db: DbSession) -> AlertDetail:
    return alert_service.resolve(db, alert_id, actor=data.actor, notes=data.notes)


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertDetail)
def dismiss_alert(alert_id: UUID, data: AlertDismissRequest, db: DbSession) -> AlertDetail:
    return alert_service.dismiss(db, alert_id, actor=data.actor, notes=data.notes)


@router.get("/alerts/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: UUID, db: DbSession) -> AlertDetail:
    return alert_service.get_alert(db, alert_id)
