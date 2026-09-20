from typing import Final

TARGET_NAME: Final = "NEXT_DEVIATION"
FEATURE_SCHEMA_VERSION: Final = "next-deviation-features-v1"
RANDOM_STATE: Final = 42

CATEGORICAL_FEATURES: Final = [
    "current_stage_code",
    "previous_stage_code",
    "source",
    "current_resource",
    "assigned_resource",
]

NUMERIC_FEATURES: Final = [
    "current_stage_sequence",
    "current_stage_sla_hours",
    "previous_stage_sequence",
    "events_so_far",
    "stage_changes_so_far",
    "unique_stages_seen",
    "current_stage_occurrences_so_far",
    "elapsed_case_hours",
    "current_stage_elapsed_hours",
    "gap_from_previous_event_hours",
    "previous_stage_duration_hours",
    "mean_completed_stage_duration_hours",
    "max_completed_stage_duration_hours",
    "process_progress_ratio",
    "prior_stage_skip_count",
    "prior_backtrack_count",
    "prior_rework_count",
    "prior_sla_breach_count",
    "prior_inactivity_count",
    "prior_structural_deviation_count",
    "prior_temporal_deviation_count",
    "hour_of_day",
    "day_of_week",
]

FEATURE_NAMES: Final = CATEGORICAL_FEATURES + NUMERIC_FEATURES
FORBIDDEN_FEATURES: Final = {
    "case_code", "case_id", "event_id", "future_stage", "next_stage",
    "final_stage", "future_event_count", "future_deviation_count",
    "total_case_duration_final", "closed_at", "target", "ground_truth",
    "scenario", "variant", "next_event_timestamp", "next_event_duration",
}

RISK_THRESHOLDS: Final = {"medium": 0.40, "high": 0.70}
MIN_CLASS_SAMPLES: Final = 30
SEVERE_IMBALANCE_PERCENTAGE: Final = 90.0
