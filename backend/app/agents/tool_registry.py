from functools import lru_cache

from app.agents.tool_schemas import (
    CaseCodeInput,
    CaseListInput,
    EmptyInput,
    TransitionListInput,
    VariantListInput,
)
from app.agents.tools import alerts, cases, deviations, predictions, process_mining
from app.agents.types import ToolDefinition


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition]) -> None:
        self._definitions = {definition.name: definition for definition in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("Los nombres de tools deben ser únicos")

    def get(self, name: str) -> ToolDefinition | None:
        return self._definitions.get(name)

    def schemas(self) -> list[dict[str, object]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": definition.name,
                    "description": definition.description,
                    "parameters": definition.input_model.model_json_schema(),
                    "strict": True,
                },
            }
            for definition in self._definitions.values()
        ]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._definitions)


@lru_cache
def get_tool_registry() -> ToolRegistry:
    return ToolRegistry(
        [
            ToolDefinition(
                "get_case",
                "Consulta datos registrados de un caso comercial por su código exacto.",
                CaseCodeInput,
                cases.get_case,
            ),
            ToolDefinition(
                "get_case_timeline",
                "Consulta cronológicamente eventos ya registrados para un caso.",
                CaseListInput,
                cases.get_case_timeline,
            ),
            ToolDefinition(
                "get_case_conformance",
                "Consulta la conformidad y desviaciones estructurales/temporales registradas.",
                CaseCodeInput,
                cases.get_case_conformance,
            ),
            ToolDefinition(
                "get_case_deviations",
                "Consulta las desviaciones determinísticas persistidas de un caso.",
                CaseListInput,
                deviations.get_case_deviations,
            ),
            ToolDefinition(
                "get_case_prediction",
                "Consulta la predicción persistida más reciente sin calcular una nueva.",
                CaseCodeInput,
                predictions.get_case_prediction,
            ),
            ToolDefinition(
                "get_case_alerts",
                "Consulta el historial read-only de alertas de un caso.",
                CaseCodeInput,
                alerts.get_case_alerts,
            ),
            ToolDefinition(
                "get_process_summary",
                "Consulta métricas agregadas existentes de minería de procesos.",
                EmptyInput,
                process_mining.get_process_summary,
            ),
            ToolDefinition(
                "get_process_variants",
                "Consulta variantes reales ordenadas por frecuencia descendente.",
                VariantListInput,
                process_mining.get_process_variants,
            ),
            ToolDefinition(
                "get_process_transitions",
                "Consulta transiciones reales ordenadas por frecuencia o duración media.",
                TransitionListInput,
                process_mining.get_process_transitions,
            ),
            ToolDefinition(
                "get_deviation_summary",
                "Consulta conteos agregados actuales de desviaciones registradas.",
                EmptyInput,
                deviations.get_deviation_summary,
            ),
            ToolDefinition(
                "get_alert_summary",
                "Consulta el resumen actual y read-only de alertas.",
                EmptyInput,
                alerts.get_alert_summary,
            ),
        ]
    )
