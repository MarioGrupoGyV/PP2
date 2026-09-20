import hashlib
import json
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sklearn.model_selection import train_test_split
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.ml.constants import (
    FEATURE_NAMES,
    FORBIDDEN_FEATURES,
    MIN_CLASS_SAMPLES,
    RANDOM_STATE,
    SEVERE_IMBALANCE_PERCENTAGE,
)
from app.ml.domain import (
    DatasetAudit,
    DatasetSplit,
    MlCase,
    MlDataset,
    MlDeviation,
    MlEvent,
    SnapshotSample,
)
from app.ml.features import build_features
from app.models.commercial_case import CommercialCase
from app.models.deviation import Deviation
from app.models.enums import EventType
from app.models.event import Event
from app.models.process_stage import ProcessStage


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def load_ml_records(
    db: Session,
) -> tuple[list[MlCase], list[MlEvent], list[MlDeviation], int]:
    cases = [
        MlCase(item.id, item.case_code, item.source, item.assigned_resource, _utc(item.started_at))
        for item in db.scalars(select(CommercialCase).order_by(CommercialCase.case_code)).all()
    ]
    stored_events = db.scalars(
        select(Event)
        .options(joinedload(Event.stage))
        .order_by(Event.case_id, Event.timestamp, Event.created_at, Event.id)
    ).all()
    events = [
        MlEvent(
            item.id, item.case_id, item.stage_id, item.stage.code,
            item.stage.sequence, item.stage.sla_hours, item.event_type,
            item.resource, _utc(item.timestamp), _utc(item.created_at),
        )
        for item in stored_events
    ]
    deviations = [
        MlDeviation(item.id, item.case_id, item.type, _utc(item.detected_at))
        for item in db.scalars(
            select(Deviation).order_by(Deviation.case_id, Deviation.detected_at, Deviation.id)
        ).all()
    ]
    maximum_sequence = db.scalar(
        select(ProcessStage.sequence)
        .where(ProcessStage.active.is_(True))
        .order_by(ProcessStage.sequence.desc())
        .limit(1)
    ) or 1
    return cases, events, deviations, maximum_sequence


def _next_stage_change(events: list[MlEvent], timestamp: datetime) -> MlEvent | None:
    return next(
        (
            event for event in events
            if event.event_type == EventType.STAGE_CHANGE and event.timestamp > timestamp
        ),
        None,
    )


def _dataset_hash(samples: list[SnapshotSample]) -> str:
    rows = [
        {
            "case_id": str(item.case_id),
            "snapshot_timestamp": item.snapshot_timestamp.isoformat(),
            "snapshot_event_id": str(item.snapshot_event_id) if item.snapshot_event_id else None,
            "target": item.target,
            "features": {name: item.features[name] for name in FEATURE_NAMES},
        }
        for item in sorted(
            samples,
            key=lambda sample: (
                str(sample.case_id),
                sample.snapshot_timestamp,
                str(sample.snapshot_event_id or ""),
            ),
        )
    ]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def audit_leakage(samples: list[SnapshotSample]) -> bool:
    for sample in samples:
        if sample.max_feature_event_timestamp > sample.snapshot_timestamp:
            return False
        if (
            sample.max_feature_deviation_detected_at is not None
            and sample.max_feature_deviation_detected_at > sample.snapshot_timestamp
        ):
            return False
        if FORBIDDEN_FEATURES.intersection(sample.features):
            return False
        if list(sample.features) != FEATURE_NAMES:
            return False
    return True


def build_dataset_from_records(
    cases: list[MlCase],
    events: list[MlEvent],
    deviations: list[MlDeviation],
    *,
    max_stage_sequence: int,
    snapshot_interval_hours: int,
    inactivity_hours: int,
) -> MlDataset:
    events_by_case: dict[UUID, list[MlEvent]] = defaultdict(list)
    deviations_by_case: dict[UUID, list[MlDeviation]] = defaultdict(list)
    for event in events:
        events_by_case[event.case_id].append(event)
    for deviation in deviations:
        deviations_by_case[deviation.case_id].append(deviation)
    for values in events_by_case.values():
        values.sort(key=lambda item: (item.timestamp, item.created_at, str(item.id)))
    for values in deviations_by_case.values():
        values.sort(key=lambda item: (item.detected_at, str(item.id)))

    samples: list[SnapshotSample] = []
    censored = 0
    temporal_exclusions = 0
    checkpoints_generated = 0
    interval = timedelta(hours=snapshot_interval_hours)

    for commercial_case in cases:
        case_events = events_by_case.get(commercial_case.id, [])
        case_deviations = deviations_by_case.get(commercial_case.id, [])
        candidates: list[tuple[datetime, UUID | None, bool]] = []
        for index, event in enumerate(case_events):
            next_change = _next_stage_change(case_events, event.timestamp)
            if next_change is None:
                censored += 1
            else:
                candidates.append((event.timestamp, event.id, False))

            if index + 1 >= len(case_events):
                continue
            checkpoint = event.timestamp + interval
            next_event_timestamp = case_events[index + 1].timestamp
            while checkpoint < next_event_timestamp:
                checkpoints_generated += 1
                if _next_stage_change(case_events, checkpoint) is not None:
                    candidates.append((checkpoint, None, True))
                else:
                    censored += 1
                checkpoint += interval

        for timestamp, snapshot_event_id, is_checkpoint in candidates:
            next_change = _next_stage_change(case_events, timestamp)
            if next_change is None:
                continue
            try:
                feature_values, max_event_timestamp, max_deviation_timestamp = build_features(
                    commercial_case,
                    case_events,
                    case_deviations,
                    timestamp,
                    max_stage_sequence,
                )
            except ValueError:
                temporal_exclusions += 1
                continue
            if (
                feature_values["current_stage_elapsed_hours"]
                > feature_values["current_stage_sla_hours"]
                or feature_values["gap_from_previous_event_hours"] > inactivity_hours
            ):
                temporal_exclusions += 1
                continue
            future_deviations = [
                item for item in case_deviations
                if timestamp < item.detected_at <= next_change.timestamp
            ]
            target_types = tuple(sorted({item.type.value for item in future_deviations}))
            samples.append(
                SnapshotSample(
                    case_id=commercial_case.id,
                    case_code=commercial_case.case_code,
                    snapshot_timestamp=timestamp,
                    snapshot_event_id=snapshot_event_id,
                    next_stage_change_timestamp=next_change.timestamp,
                    features=feature_values,
                    target=int(bool(future_deviations)),
                    target_types=target_types,
                    is_checkpoint=is_checkpoint,
                    max_feature_event_timestamp=max_event_timestamp,
                    max_feature_deviation_detected_at=max_deviation_timestamp,
                )
            )

    samples.sort(
        key=lambda item: (
            item.case_code,
            item.snapshot_timestamp,
            str(item.snapshot_event_id or ""),
        )
    )
    positive = sum(item.target for item in samples)
    negative = len(samples) - positive
    unique_cases = len({item.case_id for item in samples})
    positive_percentage = round(positive * 100 / len(samples), 4) if samples else 0.0
    warnings: list[str] = []
    if positive_percentage > SEVERE_IMBALANCE_PERCENTAGE or (
        samples and 100 - positive_percentage > SEVERE_IMBALANCE_PERCENTAGE
    ):
        warnings.append("One target class exceeds 90% of snapshots")
    leakage_passed = audit_leakage(samples)
    if not leakage_passed:
        warnings.append("Leakage audit failed")
    usable = positive >= MIN_CLASS_SAMPLES and negative >= MIN_CLASS_SAMPLES and leakage_passed
    if positive < MIN_CLASS_SAMPLES or negative < MIN_CLASS_SAMPLES:
        warnings.append("Dataset does not contain at least 30 samples per class")
    audit = DatasetAudit(
        total_snapshots=len(samples),
        positive_snapshots=positive,
        negative_snapshots=negative,
        positive_percentage=positive_percentage,
        negative_percentage=round(100 - positive_percentage, 4) if samples else 0.0,
        unique_cases=unique_cases,
        average_snapshots_per_case=round(len(samples) / unique_cases, 4) if unique_cases else 0.0,
        censored_snapshots=censored,
        temporal_rule_exclusions=temporal_exclusions,
        checkpoints_generated=checkpoints_generated,
        leakage_checks_passed=leakage_passed,
        dataset_usable=usable,
        warnings=tuple(warnings),
    )
    return MlDataset(samples=samples, audit=audit, dataset_hash=_dataset_hash(samples))


def build_dataset(db: Session, *, snapshot_interval_hours: int, inactivity_hours: int) -> MlDataset:
    cases, events, deviations, maximum_sequence = load_ml_records(db)
    return build_dataset_from_records(
        cases,
        events,
        deviations,
        max_stage_sequence=maximum_sequence,
        snapshot_interval_hours=snapshot_interval_hours,
        inactivity_hours=inactivity_hours,
    )


def _safe_split_case_ids(
    case_ids: list[UUID],
    labels: list[int],
    test_size: float,
) -> tuple[list[UUID], list[UUID]]:
    stratify = labels if len(set(labels)) > 1 and min(labels.count(0), labels.count(1)) >= 2 else None
    try:
        return train_test_split(
            case_ids,
            test_size=test_size,
            random_state=RANDOM_STATE,
            stratify=stratify,
        )
    except ValueError:
        shuffled = list(case_ids)
        random.Random(RANDOM_STATE).shuffle(shuffled)
        boundary = max(1, round(len(shuffled) * (1 - test_size)))
        return shuffled[:boundary], shuffled[boundary:]


def split_dataset(samples: list[SnapshotSample]) -> DatasetSplit:
    case_has_positive: dict[UUID, int] = defaultdict(int)
    for sample in samples:
        case_has_positive[sample.case_id] = max(case_has_positive[sample.case_id], sample.target)
    case_ids = sorted(case_has_positive, key=str)
    labels = [case_has_positive[case_id] for case_id in case_ids]
    train_ids, temporary_ids = _safe_split_case_ids(case_ids, labels, 0.30)
    temporary_labels = [case_has_positive[case_id] for case_id in temporary_ids]
    validation_ids, test_ids = _safe_split_case_ids(temporary_ids, temporary_labels, 0.50)
    train_set = frozenset(train_ids)
    validation_set = frozenset(validation_ids)
    test_set = frozenset(test_ids)
    if train_set & validation_set or train_set & test_set or validation_set & test_set:
        raise RuntimeError("Case overlap detected between ML splits")
    return DatasetSplit(
        train=[item for item in samples if item.case_id in train_set],
        validation=[item for item in samples if item.case_id in validation_set],
        test=[item for item in samples if item.case_id in test_set],
        train_case_ids=train_set,
        validation_case_ids=validation_set,
        test_case_ids=test_set,
    )
