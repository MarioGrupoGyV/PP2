import json
import logging
from time import perf_counter
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.agents.tool_registry import ToolRegistry
from app.agents.tool_schemas import CaseCodeInput
from app.agents.types import ToolExecution
from app.core.config import Settings
from app.core.exceptions import ApplicationError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, *, registry: ToolRegistry, settings: Settings) -> None:
        self.registry = registry
        self.settings = settings

    def execute(
        self,
        db: Session,
        *,
        name: str,
        arguments: Any,
        required_case_code: str | None = None,
    ) -> ToolExecution:
        started = perf_counter()
        definition = self.registry.get(name)
        if definition is None:
            logger.warning("Analyst requested unknown tool: %s", name)
            return self._result(
                name=name,
                status="error",
                started=started,
                output={"status": "error", "message": "Herramienta no disponible."},
            )
        try:
            parsed = self._parse_arguments(arguments)
            validated = definition.input_model.model_validate(parsed)
        except (ValueError, TypeError, json.JSONDecodeError, ValidationError) as exc:
            logger.info("Invalid arguments for analyst tool %s: %s", name, type(exc).__name__)
            return self._result(
                name=name,
                status="invalid_arguments",
                started=started,
                output={
                    "status": "invalid_arguments",
                    "message": "Los argumentos de la herramienta no son válidos.",
                },
            )
        if (
            required_case_code
            and isinstance(validated, CaseCodeInput)
            and validated.case_code != required_case_code
        ):
            logger.info("Analyst tool %s used a different case_code", name)
            return self._result(
                name=name,
                status="invalid_arguments",
                started=started,
                output={
                    "status": "invalid_arguments",
                    "message": (
                        "El case_code no coincide con el caso solicitado. "
                        f"Reintenta usando exactamente {required_case_code}."
                    ),
                },
            )
        try:
            payload = definition.handler(db, validated, self.settings)
            return self._result(
                name=name,
                status=payload.status,
                started=started,
                output=payload.data,
                evidence=payload.evidence,
            )
        except ResourceNotFoundError as exc:
            return self._result(
                name=name,
                status="not_found",
                started=started,
                output={"status": "not_found", "message": exc.message},
            )
        except ApplicationError as exc:
            logger.info("Analyst tool %s failed with domain error", name)
            return self._result(
                name=name,
                status="error",
                started=started,
                output={"status": "error", "message": exc.message},
            )
        except Exception as exc:
            logger.exception("Unexpected analyst tool failure: %s", name)
            return self._result(
                name=name,
                status="error",
                started=started,
                output={
                    "status": "error",
                    "message": "No pude consultar la información solicitada.",
                },
            )

    @staticmethod
    def _parse_arguments(arguments: Any) -> dict[str, Any]:
        if arguments is None:
            return {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be an object")
        return arguments

    @staticmethod
    def _result(
        *,
        name: str,
        status: str,
        started: float,
        output: dict[str, Any],
        evidence: list[dict[str, Any]] | None = None,
    ) -> ToolExecution:
        safe_status = status if status in {
            "success", "not_found", "invalid_arguments", "error"
        } else "error"
        return ToolExecution(
            name=name,
            status=safe_status,
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
            output=output,
            evidence=evidence or [],
        )
