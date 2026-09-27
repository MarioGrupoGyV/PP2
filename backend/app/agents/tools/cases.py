from sqlalchemy.orm import Session

from app.agents.tool_schemas import CaseCodeInput, CaseListInput
from app.agents.types import ToolPayload
from app.core.config import Settings
from app.services import (
    commercial_case_service,
    deviation_service,
    event_service,
    process_stage_service,
)


def _case(db: Session, case_code: str):
    return commercial_case_service.get_commercial_case_by_code(db, case_code)


def get_case(db: Session, data: CaseCodeInput, _: Settings) -> ToolPayload:
    item = _case(db, data.case_code)
    stage = process_stage_service.get_process_stage(db, item.current_stage_id)
    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(item.id),
            "case_code": item.case_code,
            "case_status": item.status.value,
            "current_stage": {"code": stage.code, "name": stage.name},
            "source": item.source,
            "assigned_resource": item.assigned_resource,
            "started_at": item.started_at.isoformat(),
            "closed_at": item.closed_at.isoformat() if item.closed_at else None,
        },
        evidence=[{"type": "case", "case_code": item.case_code, "case_id": str(item.id)}],
    )


def get_case_timeline(db: Session, data: CaseListInput, settings: Settings) -> ToolPayload:
    item = _case(db, data.case_code)
    stages = {stage.id: stage for stage in process_stage_service.list_process_stages(db)}
    limit = min(data.limit, settings.analyst_max_tool_result_items)
    all_events = event_service.list_case_events(db, item.id)
    events = all_events[:limit]
    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(item.id),
            "case_code": item.case_code,
            "returned_items": len(events),
            "truncated": len(all_events) > limit,
            "timeline": [
                {
                    "stage_code": stages[event.stage_id].code,
                    "stage_name": stages[event.stage_id].name,
                    "activity": event.activity,
                    "event_type": event.event_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "resource": event.resource,
                }
                for event in events
            ],
        },
        evidence=[{"type": "timeline", "case_code": item.case_code, "case_id": str(item.id)}],
    )


def get_case_conformance(db: Session, data: CaseCodeInput, settings: Settings) -> ToolPayload:
    item = _case(db, data.case_code)
    result = deviation_service.get_case_conformance(db, item.id)
    limit = settings.analyst_max_tool_result_items

    def compact(items):
        return [
            {
                "type": deviation.type.value,
                "severity": deviation.severity.value,
                "stage": deviation.stage_code,
                "description": deviation.description,
                "detected_at": deviation.detected_at.isoformat(),
            }
            for deviation in items[:limit]
        ]

    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(item.id),
            "case_code": item.case_code,
            "observed_sequence": result.observed_sequence,
            "expected_sequence": result.expected_sequence,
            "structurally_conforming": result.structurally_conforming,
            "structural_deviations": compact(result.structural_deviations),
            "temporal_deviations": compact(result.temporal_deviations),
        },
        evidence=[{"type": "conformance", "case_code": item.case_code, "case_id": str(item.id)}],
    )
