from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class PredictionRequest(BaseModel):
    as_of: datetime | None = None


class RiskFactor(BaseModel):
    feature: str
    value: Any
    influence: float | None = None
    importance: float | None = None
    direction: str | None = None
    scope: str


class PredictionRead(BaseModel):
    id: UUID | None
    case_id: UUID
    case_code: str
    snapshot_timestamp: datetime
    model_version: str
    algorithm: str
    risk_score: float | None
    risk_level: RiskLevel | None
    predicted_label: bool | None
    decision_threshold: float
    prediction_applicable: bool
    reason: str | None = None
    top_factors: list[RiskFactor] = Field(default_factory=list)
    predicted_at: datetime | None = None
    prediction_reused: bool = False


class PredictionList(BaseModel):
    items: list[PredictionRead]
    page: int
    page_size: int
    total: int


class ActiveModelRead(BaseModel):
    model_version: str
    algorithm: str
    target_name: str
    feature_schema_version: str
    dataset_hash: str
    trained_at: datetime
    decision_threshold: float
    test_metrics: dict[str, Any]
    predictive_quality_warning: bool


class ModelEvaluationRead(BaseModel):
    model_version: str
    selected_model: str
    validation_metrics: dict[str, Any]
    test_metrics: dict[str, Any]
    confusion_matrix: list[list[int]]
    class_distribution: dict[str, Any]
    split_summary: dict[str, Any]
    selection_reason: str
