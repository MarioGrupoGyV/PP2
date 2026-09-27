from sqlalchemy.orm import Session

from app.agents.tool_schemas import CaseCodeInput, EmptyInput
from app.agents.types import ToolPayload
from app.core.config import Settings
from app.services import alert_service, commercial_case_service


def get_case_alerts(db: Session, data: CaseCodeInput, settings: Settings) -> ToolPayload:
    commercial_case = commercial_case_service.get_commercial_case_by_code(db, data.case_code)
    items = alert_service.alerts_for_case(db, commercial_case.id)
    selected = items[: settings.analyst_max_tool_result_items]
    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(commercial_case.id),
            "case_code": commercial_case.case_code,
            "total": len(items),
            "alerts": [
                {
                    "alert_code": item.alert_code,
                    "status": item.status.value,
                    "risk_score": item.risk_score,
                    "risk_level": item.risk_level.value,
                    "triggered_at": item.triggered_at.isoformat(),
                    "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
                    "dismissed_at": item.dismissed_at.isoformat() if item.dismissed_at else None,
                }
                for item in selected
            ],
        },
        evidence=[{
            "type": "alerts",
            "case_code": commercial_case.case_code,
            "case_id": str(commercial_case.id),
            "alert_code": selected[-1].alert_code if selected else None,
        }],
    )


def get_alert_summary(db: Session, _: EmptyInput, __: Settings) -> ToolPayload:
    summary = alert_service.get_summary(db)
    return ToolPayload(
        data={"status": "success", **summary.model_dump(mode="json")},
        evidence=[{"type": "alert_summary"}],
    )
