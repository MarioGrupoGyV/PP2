from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.ml.constants import FEATURE_NAMES, FORBIDDEN_FEATURES
from app.ml.dataset import audit_leakage, build_dataset_from_records, split_dataset
from app.ml.domain import MlCase, MlDeviation, MlEvent
from app.ml.features import build_features
from app.models.enums import DeviationType, EventType

BASE = datetime(2026, 9, 1, 8, tzinfo=UTC)


def event(case_id, hours: float, sequence: int, *, event_type=EventType.STAGE_CHANGE, sla=100):
    timestamp = BASE + timedelta(hours=hours)
    return MlEvent(
        uuid4(), case_id, uuid4(), f"S{sequence}", sequence, sla,
        event_type, "Asesor", timestamp, timestamp,
    )


def case(case_id=None):
    identifier = case_id or uuid4()
    return MlCase(identifier, f"CASE-{str(identifier)[:6]}", "WEB", "Asesor", BASE)


def test_snapshot_uses_only_past_and_future_event_does_not_change_features() -> None:
    commercial_case = case()
    past = event(commercial_case.id, 0, 1)
    future = event(commercial_case.id, 24, 2)
    before, max_event, max_deviation = build_features(
        commercial_case, [past], [], BASE, 3
    )
    with_future, _, _ = build_features(
        commercial_case, [past, future], [], BASE, 3
    )
    assert before == with_future
    assert max_event == BASE
    assert max_deviation is None
    assert not FORBIDDEN_FEATURES.intersection(before)
    assert list(before) == FEATURE_NAMES


def test_future_deviation_is_not_a_feature() -> None:
    commercial_case = case()
    first = event(commercial_case.id, 0, 1)
    future_deviation = MlDeviation(
        uuid4(), commercial_case.id, DeviationType.BACKTRACK, BASE + timedelta(hours=10)
    )
    features, _, maximum = build_features(
        commercial_case, [first], [future_deviation], BASE, 3
    )
    assert features["prior_backtrack_count"] == 0
    assert maximum is None


def test_target_checkpoints_and_final_snapshot_censorship() -> None:
    commercial_case = case()
    first = event(commercial_case.id, 0, 1)
    second = event(commercial_case.id, 24, 2)
    deviation = MlDeviation(
        uuid4(), commercial_case.id, DeviationType.STAGE_SKIP, second.timestamp
    )
    dataset = build_dataset_from_records(
        [commercial_case], [first, second], [deviation],
        max_stage_sequence=3, snapshot_interval_hours=12, inactivity_hours=72,
    )
    assert dataset.audit.censored_snapshots == 1
    assert dataset.audit.checkpoints_generated == 1
    assert len(dataset.samples) == 2
    assert [sample.target for sample in dataset.samples] == [1, 1]
    assert dataset.samples[1].is_checkpoint is True
    assert audit_leakage(dataset.samples) is True


def test_checkpoint_after_sla_is_excluded_as_non_predictive() -> None:
    commercial_case = case()
    first = event(commercial_case.id, 0, 1, sla=10)
    second = event(commercial_case.id, 24, 2, sla=100)
    dataset = build_dataset_from_records(
        [commercial_case], [first, second], [],
        max_stage_sequence=2, snapshot_interval_hours=12, inactivity_hours=72,
    )
    assert dataset.audit.checkpoints_generated == 1
    assert dataset.audit.temporal_rule_exclusions == 1
    assert len(dataset.samples) == 1


def test_dataset_hash_is_deterministic() -> None:
    commercial_case = case()
    records = [event(commercial_case.id, 0, 1), event(commercial_case.id, 24, 2)]
    first = build_dataset_from_records(
        [commercial_case], records, [], max_stage_sequence=2,
        snapshot_interval_hours=12, inactivity_hours=72,
    )
    second = build_dataset_from_records(
        [commercial_case], list(reversed(records)), [], max_stage_sequence=2,
        snapshot_interval_hours=12, inactivity_hours=72,
    )
    assert first.dataset_hash == second.dataset_hash


def test_split_never_places_a_case_in_multiple_sets() -> None:
    cases = [case() for _ in range(40)]
    events = []
    deviations = []
    for index, commercial_case in enumerate(cases):
        first = event(commercial_case.id, 0, 1)
        second = event(commercial_case.id, 24, 2)
        events.extend([first, second])
        if index % 2:
            deviations.append(
                MlDeviation(uuid4(), commercial_case.id, DeviationType.REWORK, second.timestamp)
            )
    dataset = build_dataset_from_records(
        cases, events, deviations, max_stage_sequence=2,
        snapshot_interval_hours=12, inactivity_hours=72,
    )
    split = split_dataset(dataset.samples)
    assert not split.train_case_ids & split.validation_case_ids
    assert not split.train_case_ids & split.test_case_ids
    assert not split.validation_case_ids & split.test_case_ids
