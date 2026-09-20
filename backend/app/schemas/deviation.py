from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeviationSeverity, DeviationType


class DeviationRead(BaseModel):
    id: UUID
    case_id: UUID
    case_code: str
    event_id: UUID | None
    stage_id: UUID | None
    stage_code: str | None
    type: DeviationType
    severity: DeviationSeverity
    description: str
    expected_value: dict[str, object] | None
    actual_value: dict[str, object] | None
    details: dict[str, object] | None
    fingerprint: str
    detected_at: datetime
    resolved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviationList(BaseModel):
    items: list[DeviationRead]
    page: int
    page_size: int
    total: int


class AnalyzeDeviationsResult(BaseModel):
    cases_analyzed: int
    deviations_detected: int
    deviations_created: int
    deviations_existing: int


class DeviationSummary(BaseModel):
    total_deviations: int
    affected_cases: int
    structural_deviations: int
    temporal_deviations: int
    by_type: dict[str, int]
    by_severity: dict[str, int]


class ConformanceSummary(BaseModel):
    total_cases: int
    structurally_conforming_cases: int
    structurally_nonconforming_cases: int
    structural_conformance_percentage: float
    cases_with_temporal_deviations: int
    deviations: dict[str, int]


class CaseConformance(BaseModel):
    case_id: UUID
    case_code: str
    expected_sequence: list[str]
    observed_sequence: list[str]
    structurally_conforming: bool
    structural_deviations: list[DeviationRead]
    temporal_deviations: list[DeviationRead]
