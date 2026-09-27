import json
import re
import unicodedata
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.agents.analyst_prompt import SYSTEM_PROMPT
from app.agents.tool_executor import ToolExecutor
from app.agents.tool_registry import ToolRegistry
from app.agents.types import LLMClient
from app.core.config import Settings
from app.core.exceptions import (
    AnalystExecutionError,
    AnalystUnavailableError,
    DomainValidationError,
)
from app.schemas.analyst import (
    AnalystChatRequest,
    AnalystChatResponse,
    AnalystEvidence,
    AnalystStatusResponse,
    AnalystToolTrace,
)

CONTROLLED_FAILURE = "No pude consultar la información solicitada."
TOOL_LIMIT_MESSAGE = "No pude completar la consulta dentro del límite de herramientas."


class ProcessAnalystAgent:
    """Único agente del Sprint 8; interpreta, usa tools y explica."""

    def __init__(
        self,
        *,
        settings: Settings,
        client: LLMClient,
        registry: ToolRegistry,
    ) -> None:
        self.settings = settings
        self.client = client
        self.registry = registry
        self.executor = ToolExecutor(registry=registry, settings=settings)

    def status(self) -> AnalystStatusResponse:
        configured = bool(
            self.settings.analyst_llm_provider == "ollama"
            and self.settings.ollama_base_url
            and self.settings.ollama_model
        )
        if not self.settings.analyst_enabled:
            return AnalystStatusResponse(
                enabled=False,
                configured=configured,
                model=self.settings.ollama_model,
                available=False,
                message="Analista IA deshabilitado.",
            )
        if not configured:
            return AnalystStatusResponse(
                enabled=True,
                configured=False,
                model=self.settings.ollama_model,
                available=False,
                message="Analista IA no configurado.",
            )
        available, message = self.client.model_available(self.settings.ollama_model)
        return AnalystStatusResponse(
            enabled=True,
            configured=True,
            model=self.settings.ollama_model,
            available=available,
            message=message,
        )

    def chat(self, db: Session, request: AnalystChatRequest) -> AnalystChatResponse:
        if not self.settings.analyst_enabled:
            raise AnalystUnavailableError("Analista IA no configurado.")
        if len(request.history) > self.settings.analyst_max_history_messages:
            raise DomainValidationError(
                "El historial supera ANALYST_MAX_HISTORY_MESSAGES."
            )

        started = perf_counter()
        messages = self._initial_messages(request)
        traces: list[AnalystToolTrace] = []
        evidence: list[AnalystEvidence] = []
        tool_rounds = 0
        successful_tools = 0
        not_found_messages: list[str] = []
        tool_errors = 0
        tool_outputs: dict[str, dict[str, Any]] = {}
        required_case_code = self._requested_case_code(request)

        while True:
            response = self.client.chat(
                model=self.settings.ollama_model,
                messages=messages,
                tools=self.registry.schemas(),
                temperature=self.settings.analyst_temperature,
            )
            if not response.tool_calls:
                if not response.content:
                    raise AnalystExecutionError("El modelo local devolvió una respuesta vacía.")
                if not successful_tools and not_found_messages:
                    answer = "No encontré el dato solicitado. " + " ".join(
                        dict.fromkeys(not_found_messages)
                    )
                elif (tool_errors and not successful_tools) or (
                    not successful_tools and self._requires_tool(request.message)
                ):
                    answer = CONTROLLED_FAILURE
                else:
                    answer = self._ground_standard_answer(
                        request.message,
                        response.content,
                        tool_outputs,
                    )
                    answer = self._apply_language_policy(answer)
                return AnalystChatResponse(
                    answer=answer,
                    model=self.settings.ollama_model,
                    tool_calls=traces,
                    evidence=self._unique_evidence(evidence),
                    duration_ms=max(0, round((perf_counter() - started) * 1000)),
                    tool_rounds=tool_rounds,
                )

            if tool_rounds >= self.settings.analyst_max_tool_rounds:
                return AnalystChatResponse(
                    answer=TOOL_LIMIT_MESSAGE,
                    model=self.settings.ollama_model,
                    tool_calls=traces,
                    evidence=self._unique_evidence(evidence),
                    duration_ms=max(0, round((perf_counter() - started) * 1000)),
                    tool_rounds=tool_rounds,
                )

            tool_rounds += 1
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "function": {
                                "name": call.name,
                                "arguments": call.arguments,
                            }
                        }
                        for call in response.tool_calls
                    ],
                }
            )
            for call in response.tool_calls:
                execution = self.executor.execute(
                    db,
                    name=call.name,
                    arguments=call.arguments,
                    required_case_code=required_case_code,
                )
                traces.append(
                    AnalystToolTrace(
                        name=execution.name,
                        status=execution.status,
                        duration_ms=execution.duration_ms,
                    )
                )
                if execution.status in {"success", "not_found"}:
                    if execution.status == "success":
                        successful_tools += 1
                    else:
                        not_found_messages.append(
                            execution.output.get("message", "El registro no existe.")
                        )
                    tool_outputs[call.name] = execution.output
                    evidence.extend(
                        AnalystEvidence.model_validate(item)
                        for item in execution.evidence
                    )
                else:
                    tool_errors += 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": call.name,
                        "content": json.dumps(
                            execution.output,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    }
                )

    @staticmethod
    def _unique_evidence(items: list[AnalystEvidence]) -> list[AnalystEvidence]:
        unique: list[AnalystEvidence] = []
        seen: set[tuple[Any, ...]] = set()
        for item in items:
            key = (item.type, item.case_code, item.case_id, item.alert_code)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    @staticmethod
    def _apply_language_policy(answer: str) -> str:
        """Refuerza términos de gobernanza que un modelo local pequeño puede omitir."""
        replacements = (
            (
                r"\bdebido a (?:las siguientes|estas) causas(?: asociadas)?\b",
                "asociado con los siguientes factores",
            ),
            (r"\bcausas\b", "factores asociados"),
            (r"\bcausa\b", "factor asociado"),
            (r"\bdebido a\b", "asociado con"),
            (r"(?<!estimado )\briesgo alto\b", "riesgo estimado alto"),
            (r"(?<!estimado )\briesgo asociado\b", "riesgo estimado asociado"),
            (r"\bscore de riesgo\b", "score de riesgo estimado"),
            (r"\blo que aumenta el riesgo\b", "lo cual está asociado con mayor riesgo estimado"),
            (r"\blo que disminuye el riesgo\b", "lo cual está asociado con menor riesgo estimado"),
        )
        safe_answer = answer
        for pattern, replacement in replacements:
            safe_answer = re.sub(pattern, replacement, safe_answer, flags=re.IGNORECASE)
        return safe_answer

    @staticmethod
    def _requires_tool(question: str) -> bool:
        normalized = ProcessAnalystAgent._normalize_question(question)
        conceptual = (
            "que significa",
            "que es ",
            "define ",
            "diferencia entre",
        )
        if any(phrase in normalized for phrase in conceptual):
            return False
        domain_terms = (
            "caso", "variante", "transicion", "desviacion", "retrabajo",
            "prediccion", "riesgo", "alerta", "timeline", "proceso",
            "cuanto", "total", "porcentaje", "promedio", "frecuent",
            "actualmente", "estado", "mayor", "menor", "demo-",
        )
        return any(term in normalized for term in domain_terms)

    @staticmethod
    def _normalize_question(question: str) -> str:
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", question)
            if not unicodedata.combining(character)
        ).casefold()

    @staticmethod
    def _requested_case_code(request: AnalystChatRequest) -> str | None:
        codes = set(re.findall(r"\b[A-Z][A-Z0-9]*-[A-Z0-9]+\b", request.message.upper()))
        if len(codes) == 1:
            return next(iter(codes))
        if not codes:
            return request.context_case_code
        return None

    @staticmethod
    def _ground_standard_answer(
        question: str,
        model_answer: str,
        outputs: dict[str, dict[str, Any]],
    ) -> str:
        """Fija respuestas demostrativas sensibles a números usando solo tool output."""
        normalized = ProcessAnalystAgent._normalize_question(question)

        variants = outputs.get("get_process_variants", {}).get("variants", [])
        if "variante" in normalized and "frecuent" in normalized and variants:
            item = variants[0]
            sequence = " → ".join(item["activities"])
            return (
                f"La variante más frecuente es {sequence}: "
                f"{item['case_count']} casos ({item['percentage']} %)."
            )

        transition_output = outputs.get("get_process_transitions", {})
        transitions = transition_output.get("transitions", [])
        if (
            "transicion" in normalized
            and "duracion" in normalized
            and transition_output.get("sort_by") == "average_duration"
            and transitions
        ):
            item = transitions[0]
            return (
                f"La transición con mayor duración promedio es "
                f"{item['source']} → {item['target']}: "
                f"{item['average_duration_display']}."
            )

        summary = outputs.get("get_deviation_summary", {})
        if "retrabajo" in normalized and ("cuantos" in normalized or "cantidad" in normalized):
            counts = summary.get("affected_cases_by_type", {})
            if "REWORK" in counts:
                return (
                    f"Según las desviaciones registradas, {counts['REWORK']} casos "
                    "tienen retrabajo (tipo REWORK)."
                )

        case_deviations = outputs.get("get_case_deviations", {})
        if "desviacion" in normalized and case_deviations.get("status") == "success":
            case_code = case_deviations["case_code"]
            items = case_deviations.get("deviations", [])
            if not items:
                return f"No hay desviaciones registradas para {case_code}."
            lines = [
                f"{index}. {item['type']} ({item['severity']}) en "
                f"{item['stage']}: {item['description']}"
                for index, item in enumerate(items, start=1)
            ]
            suffix = (
                f" Se muestran {len(items)} de {case_deviations['total']} registros."
                if case_deviations.get("truncated") else ""
            )
            noun = "desviación registrada" if case_deviations["total"] == 1 else "desviaciones registradas"
            return (
                f"{case_code} tiene {case_deviations['total']} {noun}:\n"
                + "\n".join(lines) + suffix
            )

        prediction = outputs.get("get_case_prediction", {})
        if "riesgo" in normalized and prediction.get("status") == "success":
            if not prediction.get("prediction_applicable") or prediction.get("risk_score") is None:
                return (
                    f"La predicción registrada para {prediction['case_code']} "
                    "no es aplicable en este estado. "
                    f"{prediction.get('reason') or 'No hay un score de riesgo estimado disponible.'}"
                )
            level = {"HIGH": "alto", "MEDIUM": "medio", "LOW": "bajo"}.get(
                prediction.get("risk_level"), "no clasificado"
            )
            score = prediction["risk_score"]
            threshold = prediction["decision_threshold"]
            answer = (
                f"La predicción registrada para {prediction['case_code']} asigna "
                f"riesgo estimado {level} (score {score:.4f}; "
                f"umbral {threshold:.3f}). El score no es una probabilidad "
                "real calibrada."
            )
            labels = {
                "numeric__prior_backtrack_count": "retrocesos previos",
                "numeric__current_stage_occurrences_so_far": "apariciones de la etapa actual",
                "numeric__prior_rework_count": "retrabajos previos",
                "numeric__prior_structural_deviation_count": "desviaciones estructurales previas",
                "numeric__max_completed_stage_duration_hours": "duración máxima de etapa completada (horas)",
            }
            factors = prediction.get("top_factors", [])
            if factors:
                directions = {
                    "INCREASES_RISK": "asociado con mayor riesgo estimado",
                    "DECREASES_RISK": "asociado con menor riesgo estimado",
                }
                details = "; ".join(
                    f"{labels.get(item['feature'], item['feature'])} "
                    f"(valor {item['value']}, "
                    f"{directions.get(item['direction'], 'asociación registrada')})"
                    for item in factors
                )
                answer += f" Factores asociados del modelo: {details}."
            return answer

        alerts = outputs.get("get_case_alerts", {})
        if "estado" in normalized and "alerta" in normalized and alerts:
            items = alerts.get("alerts", [])
            case_code = alerts.get("case_code", "el caso")
            if not items:
                return f"No existen alertas registradas para {case_code}."
            states = ", ".join(
                f"{item['alert_code']}: {item['status']}" for item in items
            )
            return f"Alertas registradas para {case_code}: {states}."

        return model_answer

    @staticmethod
    def _initial_messages(request: AnalystChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(item.model_dump() for item in request.history)
        question = request.message
        if request.context_case_code:
            question = (
                f"Contexto auxiliar de la interfaz: caso {request.context_case_code}. "
                "Úsalo solo si la pregunta se refiere al caso.\n\n"
                f"Pregunta del usuario: {request.message}"
            )
        messages.append({"role": "user", "content": question})
        return messages
