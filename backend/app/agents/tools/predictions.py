from sqlalchemy.orm import Session

from app.agents.tool_schemas import CaseCodeInput
from app.agents.types import ToolPayload
from app.core.config import Settings
from app.core.exceptions import ResourceNotFoundError
from app.services import commercial_case_service, prediction_service


def get_case_prediction(db: Session, data: CaseCodeInput, _: Settings) -> ToolPayload:
    commercial_case = commercial_case_service.get_commercial_case_by_code(db, data.case_code)
    evidence = [{
        "type": "prediction",
        "case_code": commercial_case.case_code,
        "case_id": str(commercial_case.id),
    }]
    try:
        item = prediction_service.latest_prediction(db, commercial_case.id)
    except ResourceNotFoundError:
        return ToolPayload(
            status="not_found",
            data={
                "status": "not_found",
                "case_id": str(commercial_case.id),
                "case_code": commercial_case.case_code,
                "message": "No existe una predicción registrada para este caso.",
            },
            evidence=evidence,
        )
    return ToolPayload(
        data={
            "status": "success",
            "case_id": str(commercial_case.id),
            "case_code": commercial_case.case_code,
            "risk_score": item.risk_score,
            "risk_level": item.risk_level.value if item.risk_level else None,
            "predicted_label": item.predicted_label,
            "model_version": item.model_version,
            "snapshot_timestamp": item.snapshot_timestamp.isoformat(),
            "decision_threshold": item.decision_threshold,
            "prediction_applicable": item.prediction_applicable,
            "reason": item.reason,
            "top_factors": [factor.model_dump(mode="json") for factor in item.top_factors],
        },
        evidence=evidence,
    )
