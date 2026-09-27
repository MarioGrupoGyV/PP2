from sqlalchemy.orm import Session

from app.agents.tool_schemas import CaseListInput, EmptyInput
from app.agents.types import ToolPayload
from app.core.config import Settings
from app.services import commercial_case_service, deviation_service


def get_case_deviations(
    db: Session,
    data: CaseListInput,
    settings: Settings,
) -> ToolPayload:
    commercial_case = commercial_case_service.get_commercial_case_by_code(db, data.case_code)
    items = deviation_service.get_case_deviations(db, commercial_case.id)
    limit = min(data.limit, settings.analyst_max_tool_result_items)
    selected = items[:limit]
    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(commercial_case.id),
            "case_code": commercial_case.case_code,
            "total": len(items),
            "returned_items": len(selected),
            "truncated": len(items) > limit,
            "deviations": [
                {
                    "type": item.type.value,
                    "severity": item.severity.value,
                    "stage": item.stage_code,
                    "description": item.description,
                    "expected_value": item.expected_value,
                    "actual_value": item.actual_value,
                    "detected_at": item.detected_at.isoformat(),
                }
                for item in selected
            ],
        },
        evidence=[{
            "type": "deviations",
            "case_code": commercial_case.case_code,
            "case_id": str(commercial_case.id),
        }],
    )


def get_deviation_summary(db: Session, _: EmptyInput, __: Settings) -> ToolPayload:
    summary = deviation_service.get_summary(db)
    return ToolPayload(
        data={
            "status": "success",
            **summary.model_dump(mode="json"),
            "affected_cases_by_type": deviation_service.get_affected_case_counts_by_type(db),
        },
        evidence=[{"type": "deviation_summary"}],
    )
