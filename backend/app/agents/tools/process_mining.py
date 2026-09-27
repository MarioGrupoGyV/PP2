from sqlalchemy.orm import Session

from app.agents.tool_schemas import EmptyInput, TransitionListInput, VariantListInput
from app.agents.types import ToolPayload
from app.core.config import Settings
from app.services import process_mining_service


def _duration_display(total_seconds: float) -> str:
    if total_seconds < 60:
        return f"{round(total_seconds)} s"
    if total_seconds < 3600:
        return f"{total_seconds / 60:.1f} min"
    if total_seconds < 86400:
        return f"{total_seconds / 3600:.1f} h"
    return f"{total_seconds / 86400:.1f} días"


def get_process_summary(db: Session, _: EmptyInput, __: Settings) -> ToolPayload:
    summary = process_mining_service.get_summary(db)
    return ToolPayload(
        data={"status": "success", **summary.model_dump(mode="json")},
        evidence=[{"type": "process_summary"}],
    )


def get_process_variants(
    db: Session,
    data: VariantListInput,
    settings: Settings,
) -> ToolPayload:
    limit = min(data.limit, 20, settings.analyst_max_tool_result_items)
    items = process_mining_service.get_variants(db, limit=limit)
    return ToolPayload(
        data={
            "status": "success",
            "returned_items": len(items),
            "variants": [item.model_dump(mode="json") for item in items],
        },
        evidence=[{"type": "process_variants"}],
    )


def get_process_transitions(
    db: Session,
    data: TransitionListInput,
    settings: Settings,
) -> ToolPayload:
    items = process_mining_service.get_transitions(db)
    if data.sort_by == "average_duration":
        items.sort(key=lambda item: (-item.average_duration_seconds, item.source, item.target))
    else:
        items.sort(key=lambda item: (-item.frequency, item.source, item.target))
    limit = min(data.limit, settings.analyst_max_tool_result_items)
    selected = items[:limit]
    return ToolPayload(
        data={
            "status": "success",
            "sort_by": data.sort_by,
            "returned_items": len(selected),
            "transitions": [
                {
                    "source": item.source,
                    "target": item.target,
                    "frequency": item.frequency,
                    "case_frequency": item.case_frequency,
                    "percentage": item.percentage,
                    "average_duration_seconds": item.average_duration_seconds,
                    "average_duration_display": _duration_display(
                        item.average_duration_seconds
                    ),
                    "median_duration_seconds": item.median_duration_seconds,
                }
                for item in selected
            ],
        },
        evidence=[{"type": "process_transitions"}],
    )
