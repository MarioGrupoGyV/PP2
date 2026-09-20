from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AlertActionType, AlertEvaluationMode, AlertStatus, RiskLevel
from app.schemas.prediction import PredictionRead, RiskFactor


class AlertEvaluationRequest(BaseModel):
    as_of: datetime | None = None
    case_id: UUID | None = None
    case_ids: list[UUID] | None = Field(default=None, max_length=500)
    limit: int = Field(default=100, ge=1, le=500)


class AlertPredictionRead(BaseModel):
    id: UUID
    model_version: str
    snapshot_timestamp: datetime
    risk_score: float
    risk_level: RiskLevel
    predicted_label: bool


class AlertRead(BaseModel):
    id: UUID
    alert_code: str
    case_id: UUID
    case_code: str
    status: AlertStatus
    risk_score: float
    risk_level: RiskLevel
    title: str
    description: str
    evaluation_mode: AlertEvaluationMode
    triggered_at: datetime
    last_evaluated_at: datetime
    attended_at: datetime | None
    resolved_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AlertDetail(AlertRead):
    origin_prediction: AlertPredictionRead
    latest_prediction: AlertPredictionRead
    model_version: str
    snapshot_timestamp: datetime
    current_factors: list[RiskFactor]


class AlertList(BaseModel):
    items: list[AlertRead]
    page: int
    page_size: int
    total: int


class AlertActionRead(BaseModel):
    id: UUID
    alert_id: UUID
    action_type: AlertActionType
    actor: str | None
    notes: str | None
    previous_status: AlertStatus | None
    new_status: AlertStatus | None
    prediction_id: UUID | None
    details: dict[str, Any] | None
    created_at: datetime


class AlertActionRequest(BaseModel):
    actor: str | None = Field(default=None, max_length=150)
    notes: str = Field(min_length=1, max_length=1000)

    @field_validator("notes")
    @classmethod
    def notes_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("notes no puede estar vacío")
        return value


class AlertTransitionRequest(BaseModel):
    actor: str | None = Field(default=None, max_length=150)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class AlertDismissRequest(AlertActionRequest):
    pass


AlertEvaluationOutcome = Literal[
    "CREATED",
    "UPDATED",
    "NO_CHANGE",
    "BELOW_THRESHOLD",
    "NOT_APPLICABLE",
    "INELIGIBLE",
    "NO_OBSERVABLE_STATE",
    "CLOSED_CYCLE_NOT_NEW",
]


class AlertEvaluationRead(BaseModel):
    case_id: UUID
    case_code: str
    evaluation_mode: AlertEvaluationMode
    outcome: AlertEvaluationOutcome
    prediction: PredictionRead | None = None
    alert: AlertRead | None = None
    alert_risk_threshold: float
    message: str


class AlertBatchRead(BaseModel):
    evaluation_mode: AlertEvaluationMode
    alert_risk_threshold: float
    cases_evaluated: int
    predictions_created: int
    predictions_reused: int
    alerts_created: int
    alerts_updated: int
    below_threshold: int
    skipped_not_applicable: int
    skipped_no_observable_state: int
    skipped_ineligible: int
    unchanged: int
    cases_without_alert: int
    results: list[AlertEvaluationRead]


class AlertSummary(BaseModel):
    total_alerts: int
    active: int
    attended: int
    resolved: int
    dismissed: int
    open_alerts: int
    average_open_risk_score: float | None
    by_risk_level: dict[RiskLevel, int]
