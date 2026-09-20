import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.exceptions import PersistenceError, ResourceNotFoundError
from app.models.commercial_case import CommercialCase
from app.models.deviation import Deviation
from app.models.enums import DeviationSeverity, DeviationType, EventType
from app.models.event import Event
from app.models.process_stage import ProcessStage
from app.repositories import deviation_repository, process_stage_repository
from app.schemas.deviation import (
    AnalyzeDeviationsResult,
    CaseConformance,
    ConformanceSummary,
    DeviationList,
    DeviationRead,
    DeviationSummary,
)

logger = logging.getLogger(__name__)
STRUCTURAL_TYPES = {
    DeviationType.STAGE_SKIP,
    DeviationType.BACKTRACK,
    DeviationType.REWORK,
}


@dataclass(frozen=True, slots=True)
class TraceEvent:
    id: UUID
    case_id: UUID
    stage_id: UUID
    stage_code: str
    stage_name: str
    stage_sequence: int
    stage_sla_hours: int
    event_type: EventType
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class DeviationCandidate:
    case_id: UUID
    event_id: UUID
    stage_id: UUID
    type: DeviationType
    severity: DeviationSeverity
    description: str
    expected_value: dict[str, object] | None
    actual_value: dict[str, object] | None
    details: dict[str, object] | None
    detected_at: datetime
    fingerprint: str


def _fingerprint(
    deviation_type: DeviationType,
    case_id: UUID,
    event_id: UUID,
    related_event_id: UUID | None = None,
) -> str:
    canonical = json.dumps(
        {
            "rule_version": 1,
            "type": deviation_type.value,
            "case_id": str(case_id),
            "event_id": str(event_id),
            "related_event_id": str(related_event_id) if related_event_id else None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def duration_severity(exceeded_hours: float, threshold_hours: float) -> DeviationSeverity:
    ratio = exceeded_hours / threshold_hours
    if ratio <= 0.25:
        return DeviationSeverity.LOW
    if ratio <= 1:
        return DeviationSeverity.MEDIUM
    return DeviationSeverity.HIGH


def detect_deviations(
    trace: list[TraceEvent],
    expected_stages: list[ProcessStage],
    inactivity_hours: int,
) -> list[DeviationCandidate]:
    if not trace:
        return []
    stages_by_sequence = {stage.sequence: stage for stage in expected_stages}
    candidates: list[DeviationCandidate] = []

    for previous, current in zip(trace, trace[1:], strict=False):
        elapsed_hours = (current.timestamp - previous.timestamp).total_seconds() / 3600
        if elapsed_hours > inactivity_hours:
            exceeded = elapsed_hours - inactivity_hours
            candidates.append(
                DeviationCandidate(
                    current.case_id,
                    current.id,
                    current.stage_id,
                    DeviationType.INACTIVITY,
                    duration_severity(exceeded, inactivity_hours),
                    f"Inactividad de {elapsed_hours:.1f} horas entre eventos",
                    {"max_inactivity_hours": inactivity_hours},
                    {"inactivity_hours": round(elapsed_hours, 3)},
                    {"previous_event_id": str(previous.id)},
                    current.timestamp,
                    _fingerprint(DeviationType.INACTIVITY, current.case_id, current.id, previous.id),
                )
            )

    stage_changes = [event for event in trace if event.event_type == EventType.STAGE_CHANGE]
    seen: dict[int, TraceEvent] = {}
    occurrences: dict[int, int] = defaultdict(int)
    for current in stage_changes:
        prior = seen.get(current.stage_sequence)
        occurrences[current.stage_sequence] += 1
        if prior is not None:
            occurrence = occurrences[current.stage_sequence]
            candidates.append(
                DeviationCandidate(
                    current.case_id, current.id, current.stage_id,
                    DeviationType.REWORK,
                    DeviationSeverity.MEDIUM if occurrence == 2 else DeviationSeverity.HIGH,
                    f"Reingreso a la etapa {current.stage_code}",
                    {"maximum_occurrences": 1},
                    {"occurrence_number": occurrence, "stage_code": current.stage_code},
                    {"previous_event_id": str(prior.id), "previous_occurrence_timestamp": prior.timestamp.isoformat()}, current.timestamp,
                    _fingerprint(DeviationType.REWORK, current.case_id, current.id, prior.id),
                )
            )
        seen[current.stage_sequence] = current

    for previous, current in zip(stage_changes, stage_changes[1:], strict=False):
        difference = current.stage_sequence - previous.stage_sequence
        if difference > 1:
            missing = [
                stages_by_sequence[sequence].code
                for sequence in range(previous.stage_sequence + 1, current.stage_sequence)
                if sequence in stages_by_sequence
            ]
            candidates.append(
                DeviationCandidate(
                    current.case_id, current.id, current.stage_id,
                    DeviationType.STAGE_SKIP,
                    DeviationSeverity.MEDIUM if len(missing) == 1 else DeviationSeverity.HIGH,
                    f"Salto de {previous.stage_code} a {current.stage_code}",
                    {"expected_next": missing[0] if missing else None, "missing_stages": missing},
                    {"from": previous.stage_code, "to": current.stage_code},
                    {"previous_event_id": str(previous.id)}, current.timestamp,
                    _fingerprint(DeviationType.STAGE_SKIP, current.case_id, current.id, previous.id),
                )
            )
        elif difference < 0:
            candidates.append(
                DeviationCandidate(
                    current.case_id, current.id, current.stage_id,
                    DeviationType.BACKTRACK,
                    DeviationSeverity.MEDIUM if abs(difference) == 1 else DeviationSeverity.HIGH,
                    f"Retroceso de {previous.stage_code} a {current.stage_code}",
                    {"direction": "forward", "minimum_sequence": previous.stage_sequence},
                    {"from_stage": previous.stage_code, "to_stage": current.stage_code, "sequence_difference": difference},
                    {"previous_event_id": str(previous.id)}, current.timestamp,
                    _fingerprint(DeviationType.BACKTRACK, current.case_id, current.id, previous.id),
                )
            )
        elapsed_hours = (current.timestamp - previous.timestamp).total_seconds() / 3600
        if elapsed_hours > previous.stage_sla_hours:
            exceeded = elapsed_hours - previous.stage_sla_hours
            candidates.append(
                DeviationCandidate(
                    current.case_id, current.id, previous.stage_id,
                    DeviationType.SLA_BREACH,
                    duration_severity(exceeded, previous.stage_sla_hours),
                    f"SLA excedido en {previous.stage_code} por {exceeded:.1f} horas",
                    {"sla_hours": previous.stage_sla_hours, "stage": previous.stage_code},
                    {"duration_hours": round(elapsed_hours, 3), "exceeded_hours": round(exceeded, 3)},
                    {"previous_event_id": str(previous.id)}, current.timestamp,
                    _fingerprint(DeviationType.SLA_BREACH, current.case_id, current.id, previous.id),
                )
            )
    return candidates


def _load_traces(db: Session) -> tuple[list[CommercialCase], dict[UUID, list[TraceEvent]]]:
    cases = list(db.scalars(select(CommercialCase).order_by(CommercialCase.case_code)).all())
    events = list(
        db.scalars(
            select(Event)
            .options(joinedload(Event.stage))
            .order_by(Event.case_id, Event.timestamp, Event.created_at, Event.id)
        ).all()
    )
    traces: dict[UUID, list[TraceEvent]] = defaultdict(list)
    for event in events:
        traces[event.case_id].append(
            TraceEvent(
                event.id, event.case_id, event.stage_id, event.stage.code,
                event.stage.name, event.stage.sequence, event.stage.sla_hours,
                event.event_type, event.timestamp,
            )
        )
    return cases, traces


def analyze(db: Session) -> AnalyzeDeviationsResult:
    cases, traces = _load_traces(db)
    stages = [stage for stage in process_stage_repository.list_all(db) if stage.active]
    candidates = [
        candidate
        for case in cases
        for candidate in detect_deviations(
            traces.get(case.id, []), stages, get_settings().deviation_inactivity_hours
        )
    ]
    candidates = list({item.fingerprint: item for item in candidates}.values())
    existing = deviation_repository.existing_fingerprints(
        db, {item.fingerprint for item in candidates}
    )
    new_items = [item for item in candidates if item.fingerprint not in existing]
    deviation_repository.add_all(db, [Deviation(**asdict(item)) for item in new_items])
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Deviation analysis transaction failed: %s", type(exc).__name__)
        raise PersistenceError("No fue posible guardar el análisis de desviaciones") from exc
    return AnalyzeDeviationsResult(
        cases_analyzed=len(cases), deviations_detected=len(candidates),
        deviations_created=len(new_items), deviations_existing=len(existing)
    )


def _read(item: Deviation) -> DeviationRead:
    return DeviationRead(
        id=item.id, case_id=item.case_id, case_code=item.commercial_case.case_code,
        event_id=item.event_id, stage_id=item.stage_id,
        stage_code=item.stage.code if item.stage else None, type=item.type,
        severity=item.severity, description=item.description,
        expected_value=item.expected_value, actual_value=item.actual_value,
        details=item.details, fingerprint=item.fingerprint,
        detected_at=item.detected_at, resolved_at=item.resolved_at,
        created_at=item.created_at,
    )


def list_deviations(db: Session, *, deviation_type: DeviationType | None, severity: DeviationSeverity | None, case_code: str | None, page: int, page_size: int) -> DeviationList:
    items, total = deviation_repository.list_filtered(
        db, deviation_type=deviation_type, severity=severity, case_code=case_code,
        offset=(page - 1) * page_size, limit=page_size,
    )
    return DeviationList(items=[_read(item) for item in items], page=page, page_size=page_size, total=total)


def get_deviation(db: Session, deviation_id: UUID) -> DeviationRead:
    item = deviation_repository.get_by_id(db, deviation_id)
    if item is None:
        raise ResourceNotFoundError("Desviación no encontrada")
    return _read(item)


def get_case_deviations(db: Session, case_id: UUID) -> list[DeviationRead]:
    if db.get(CommercialCase, case_id) is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    return [_read(item) for item in deviation_repository.all_for_case(db, case_id)]


def get_summary(db: Session) -> DeviationSummary:
    total, affected_cases, by_type, by_severity = deviation_repository.summary(db)
    by_type = {item.value: by_type.get(item.value, 0) for item in DeviationType}
    by_severity = {
        item.value: by_severity.get(item.value, 0) for item in DeviationSeverity
    }
    structural = sum(by_type.get(item.value, 0) for item in STRUCTURAL_TYPES)
    return DeviationSummary(
        total_deviations=total, affected_cases=affected_cases,
        structural_deviations=structural, temporal_deviations=total - structural,
        by_type=by_type, by_severity=by_severity,
    )


def get_case_conformance(db: Session, case_id: UUID) -> CaseConformance:
    case = db.get(CommercialCase, case_id)
    if case is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    _, traces = _load_traces(db)
    observed = [event.stage_code for event in traces.get(case_id, []) if event.event_type == EventType.STAGE_CHANGE]
    expected = [stage.code for stage in process_stage_repository.list_all(db) if stage.active]
    deviations = [_read(item) for item in deviation_repository.all_for_case(db, case_id)]
    structural = [item for item in deviations if item.type in STRUCTURAL_TYPES]
    temporal = [item for item in deviations if item.type not in STRUCTURAL_TYPES]
    return CaseConformance(
        case_id=case.id, case_code=case.case_code, expected_sequence=expected,
        observed_sequence=observed, structurally_conforming=not structural,
        structural_deviations=structural, temporal_deviations=temporal,
    )


def get_conformance_summary(db: Session) -> ConformanceSummary:
    total = db.scalar(select(func.count()).select_from(CommercialCase)) or 0
    non_conforming = db.scalar(
        select(func.count(distinct(Deviation.case_id))).where(Deviation.type.in_(STRUCTURAL_TYPES))
    ) or 0
    conforming = total - non_conforming
    temporal_types = {DeviationType.SLA_BREACH, DeviationType.INACTIVITY}
    temporal_cases = db.scalar(
        select(func.count(distinct(Deviation.case_id))).where(Deviation.type.in_(temporal_types))
    ) or 0
    _, _, by_type, _ = deviation_repository.summary(db)
    return ConformanceSummary(
        total_cases=total, structurally_conforming_cases=conforming,
        structurally_nonconforming_cases=non_conforming,
        structural_conformance_percentage=round(conforming * 100 / total, 2) if total else 0.0,
        cases_with_temporal_deviations=temporal_cases,
        deviations={item.value: by_type.get(item.value, 0) for item in DeviationType},
    )
