from collections import Counter
from datetime import datetime
from typing import Any

from app.ml.constants import FEATURE_NAMES
from app.ml.domain import MlCase, MlDeviation, MlEvent
from app.models.enums import DeviationType, EventType

STRUCTURAL_TYPES = {
    DeviationType.STAGE_SKIP,
    DeviationType.BACKTRACK,
    DeviationType.REWORK,
}


def _hours(later: datetime, earlier: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds() / 3600)


def build_features(
    commercial_case: MlCase,
    events: list[MlEvent],
    deviations: list[MlDeviation],
    snapshot_timestamp: datetime,
    max_stage_sequence: int,
) -> tuple[dict[str, Any], datetime, datetime | None]:
    """Build a feature vector using records observable at snapshot_timestamp only."""
    observed_events = sorted(
        (event for event in events if event.timestamp <= snapshot_timestamp),
        key=lambda item: (item.timestamp, item.created_at, str(item.id)),
    )
    observed_deviations = sorted(
        (item for item in deviations if item.detected_at <= snapshot_timestamp),
        key=lambda item: (item.detected_at, str(item.id)),
    )
    stage_changes = [
        event for event in observed_events if event.event_type == EventType.STAGE_CHANGE
    ]
    if not observed_events or not stage_changes:
        raise ValueError("Snapshot has no observable stage")

    current_stage = stage_changes[-1]
    previous_stage = stage_changes[-2] if len(stage_changes) > 1 else None
    completed_durations = [
        _hours(current.timestamp, previous.timestamp)
        for previous, current in zip(stage_changes, stage_changes[1:], strict=False)
    ]
    stage_counts = Counter(event.stage_code for event in stage_changes)
    deviation_counts = Counter(item.type for item in observed_deviations)
    latest_event = observed_events[-1]

    raw_features: dict[str, Any] = {
        "current_stage_code": current_stage.stage_code,
        "current_stage_sequence": current_stage.stage_sequence,
        "current_stage_sla_hours": current_stage.stage_sla_hours,
        "previous_stage_code": previous_stage.stage_code if previous_stage else None,
        "previous_stage_sequence": previous_stage.stage_sequence if previous_stage else None,
        "source": commercial_case.source,
        "current_resource": latest_event.resource,
        "assigned_resource": commercial_case.assigned_resource,
        "events_so_far": len(observed_events),
        "stage_changes_so_far": len(stage_changes),
        "unique_stages_seen": len(stage_counts),
        "current_stage_occurrences_so_far": stage_counts[current_stage.stage_code],
        "elapsed_case_hours": round(_hours(snapshot_timestamp, commercial_case.started_at), 6),
        "current_stage_elapsed_hours": round(_hours(snapshot_timestamp, current_stage.timestamp), 6),
        "gap_from_previous_event_hours": round(_hours(snapshot_timestamp, latest_event.timestamp), 6),
        "previous_stage_duration_hours": round(completed_durations[-1], 6) if completed_durations else None,
        "mean_completed_stage_duration_hours": round(sum(completed_durations) / len(completed_durations), 6) if completed_durations else None,
        "max_completed_stage_duration_hours": round(max(completed_durations), 6) if completed_durations else None,
        "process_progress_ratio": round(current_stage.stage_sequence / max_stage_sequence, 6),
        "prior_stage_skip_count": deviation_counts[DeviationType.STAGE_SKIP],
        "prior_backtrack_count": deviation_counts[DeviationType.BACKTRACK],
        "prior_rework_count": deviation_counts[DeviationType.REWORK],
        "prior_sla_breach_count": deviation_counts[DeviationType.SLA_BREACH],
        "prior_inactivity_count": deviation_counts[DeviationType.INACTIVITY],
        "prior_structural_deviation_count": sum(deviation_counts[item] for item in STRUCTURAL_TYPES),
        "prior_temporal_deviation_count": deviation_counts[DeviationType.SLA_BREACH] + deviation_counts[DeviationType.INACTIVITY],
        "hour_of_day": snapshot_timestamp.hour,
        "day_of_week": snapshot_timestamp.weekday(),
    }
    features = {name: raw_features[name] for name in FEATURE_NAMES}
    return (
        features,
        latest_event.timestamp,
        observed_deviations[-1].detected_at if observed_deviations else None,
    )
