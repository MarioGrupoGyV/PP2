from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.models.enums import DeviationSeverity, DeviationType, EventType
from app.services.deviation_service import TraceEvent, detect_deviations


BASE = datetime(2026, 9, 1, 8, tzinfo=UTC)


def stages():
    return [
        SimpleNamespace(id=uuid4(), code=code, name=code.title(), sequence=index, sla_hours=sla, active=True)
        for index, (code, sla) in enumerate(
            [("LEAD", 1), ("CONTACTED", 48), ("QUALIFIED", 72), ("VISIT", 48)], start=1
        )
    ]


def trace(sequence: list[tuple[int, float, EventType]]) -> tuple[list[TraceEvent], list[object]]:
    model = stages()
    case_id = uuid4()
    events = []
    for stage_number, hours, event_type in sequence:
        stage = model[stage_number - 1]
        events.append(
            TraceEvent(uuid4(), case_id, stage.id, stage.code, stage.name, stage.sequence, stage.sla_hours, event_type, BASE + timedelta(hours=hours))
        )
    return events, model


def types_for(events, model):
    return [item.type for item in detect_deviations(events, model, 72)]


def test_stage_skip_supports_one_and_multiple_missing_stages() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (3, 1, EventType.STAGE_CHANGE)])
    one_missing = next(item for item in detect_deviations(events, model, 72) if item.type == DeviationType.STAGE_SKIP)
    assert one_missing.severity == DeviationSeverity.MEDIUM
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (4, 1, EventType.STAGE_CHANGE)])
    deviation = next(item for item in detect_deviations(events, model, 72) if item.type == DeviationType.STAGE_SKIP)
    assert deviation.severity == DeviationSeverity.HIGH
    assert deviation.expected_value == {"expected_next": "CONTACTED", "missing_stages": ["CONTACTED", "QUALIFIED"]}


def test_adjacent_and_backward_transitions_are_not_stage_skip() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (2, 1, EventType.STAGE_CHANGE), (1, 2, EventType.STAGE_CHANGE)])
    assert DeviationType.STAGE_SKIP not in types_for(events, model)
    assert DeviationType.BACKTRACK in types_for(events, model)


def test_backtrack_severity_and_rework_can_coexist() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (2, 1, EventType.STAGE_CHANGE), (4, 2, EventType.STAGE_CHANGE), (2, 3, EventType.STAGE_CHANGE)])
    found = detect_deviations(events, model, 72)
    backtrack = next(item for item in found if item.type == DeviationType.BACKTRACK)
    assert backtrack.severity == DeviationSeverity.HIGH
    assert any(item.type == DeviationType.REWORK for item in found)


def test_rework_second_is_medium_and_third_is_high() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (1, 1, EventType.STAGE_CHANGE), (1, 2, EventType.STAGE_CHANGE)])
    rework = [item for item in detect_deviations(events, model, 72) if item.type == DeviationType.REWORK]
    assert [item.severity for item in rework] == [DeviationSeverity.MEDIUM, DeviationSeverity.HIGH]


def test_sla_boundary_and_severity() -> None:
    events, model = trace([(2, 0, EventType.STAGE_CHANGE), (3, 49, EventType.STAGE_CHANGE)])
    breach = next(item for item in detect_deviations(events, model, 72) if item.type == DeviationType.SLA_BREACH)
    assert breach.severity == DeviationSeverity.LOW
    events, model = trace([(2, 0, EventType.STAGE_CHANGE), (3, 48, EventType.STAGE_CHANGE)])
    assert DeviationType.SLA_BREACH not in types_for(events, model)
    events, model = trace([(2, 0, EventType.STAGE_CHANGE), (3, 61, EventType.STAGE_CHANGE)])
    assert next(item for item in detect_deviations(events, model, 72) if item.type == DeviationType.SLA_BREACH).severity == DeviationSeverity.MEDIUM
    events, model = trace([(2, 0, EventType.STAGE_CHANGE), (3, 97, EventType.STAGE_CHANGE)])
    assert next(item for item in detect_deviations(events, model, 72) if item.type == DeviationType.SLA_BREACH).severity == DeviationSeverity.HIGH


def test_inactivity_uses_consecutive_events_and_not_current_time() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE)])
    assert detect_deviations(events, model, 72) == []
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (1, 71, EventType.INTERACTION)])
    assert DeviationType.INACTIVITY not in types_for(events, model)
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (1, 73, EventType.INTERACTION)])
    assert types_for(events, model) == [DeviationType.INACTIVITY]


def test_overlap_and_fingerprints_are_deterministic() -> None:
    events, model = trace([(1, 0, EventType.STAGE_CHANGE), (4, 120, EventType.STAGE_CHANGE)])
    first = detect_deviations(events, model, 72)
    second = detect_deviations(events, model, 72)
    assert {item.type for item in first} == {DeviationType.INACTIVITY, DeviationType.STAGE_SKIP, DeviationType.SLA_BREACH}
    assert [item.fingerprint for item in first] == [item.fingerprint for item in second]
