from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.enums import DeviationType, EventType


@dataclass(frozen=True, slots=True)
class MlCase:
    id: UUID
    case_code: str
    source: str | None
    assigned_resource: str | None
    started_at: datetime


@dataclass(frozen=True, slots=True)
class MlEvent:
    id: UUID
    case_id: UUID
    stage_id: UUID
    stage_code: str
    stage_sequence: int
    stage_sla_hours: int
    event_type: EventType
    resource: str | None
    timestamp: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class MlDeviation:
    id: UUID
    case_id: UUID
    type: DeviationType
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class SnapshotSample:
    case_id: UUID
    case_code: str
    snapshot_timestamp: datetime
    snapshot_event_id: UUID | None
    next_stage_change_timestamp: datetime
    features: dict[str, Any]
    target: int
    target_types: tuple[str, ...]
    is_checkpoint: bool
    max_feature_event_timestamp: datetime
    max_feature_deviation_detected_at: datetime | None


@dataclass(frozen=True, slots=True)
class DatasetAudit:
    total_snapshots: int
    positive_snapshots: int
    negative_snapshots: int
    positive_percentage: float
    negative_percentage: float
    unique_cases: int
    average_snapshots_per_case: float
    censored_snapshots: int
    temporal_rule_exclusions: int
    checkpoints_generated: int
    leakage_checks_passed: bool
    dataset_usable: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MlDataset:
    samples: list[SnapshotSample]
    audit: DatasetAudit
    dataset_hash: str


@dataclass(frozen=True, slots=True)
class DatasetSplit:
    train: list[SnapshotSample]
    validation: list[SnapshotSample]
    test: list[SnapshotSample]
    train_case_ids: frozenset[UUID]
    validation_case_ids: frozenset[UUID]
    test_case_ids: frozenset[UUID]
