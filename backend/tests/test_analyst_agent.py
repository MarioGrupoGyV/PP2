from sqlalchemy.orm import Session

from app.agents.analyst_agent import (
    CONTROLLED_FAILURE,
    TOOL_LIMIT_MESSAGE,
    ProcessAnalystAgent,
)
from app.agents.tool_registry import get_tool_registry
from app.core.config import Settings
from app.core.exceptions import DomainValidationError
from app.schemas.analyst import AnalystChatRequest, LLMResponse, OllamaToolCall
from tests.fakes import FakeLLMClient
from tests.process_mining_helpers import create_process_mining_data


def make_agent(fake: FakeLLMClient, **overrides) -> ProcessAnalystAgent:
    return ProcessAnalystAgent(
        settings=Settings(**overrides),
        client=fake,
        registry=get_tool_registry(),
    )


def test_agent_executes_multi_round_tool_calls_and_derives_evidence(
    db_session: Session,
) -> None:
    fake = FakeLLMClient(
        [
            LLMResponse(
                tool_calls=[OllamaToolCall(name="get_process_summary", arguments={})]
            ),
            LLMResponse(
                tool_calls=[OllamaToolCall(name="get_deviation_summary", arguments={})]
            ),
            LLMResponse(content="El proceso no contiene datos en este entorno de prueba."),
        ]
    )
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="Resume el proceso y sus desviaciones."),
    )
    assert response.tool_rounds == 2
    assert [item.name for item in response.tool_calls] == [
        "get_process_summary", "get_deviation_summary"
    ]
    assert [item.type for item in response.evidence] == [
        "process_summary", "deviation_summary"
    ]
    assert response.answer.startswith("El proceso")
    sent_tools = fake.requests[0]["tools"]
    assert len(sent_tools) == 11
    assert all(tool["function"]["strict"] for tool in sent_tools)


def test_agent_does_not_return_factual_answer_after_invalid_tool_call(
    db_session: Session,
) -> None:
    fake = FakeLLMClient(
        [
            LLMResponse(
                tool_calls=[
                    OllamaToolCall(name="get_case", arguments='{"case_code":')
                ]
            ),
            LLMResponse(content="Inventé una respuesta factual."),
        ]
    )
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Qué estado tiene CASE-1?"),
    )
    assert response.answer == CONTROLLED_FAILURE
    assert response.tool_calls[0].status == "invalid_arguments"
    assert response.evidence == []


def test_agent_stops_at_tool_round_limit(db_session: Session) -> None:
    fake = FakeLLMClient(
        [
            LLMResponse(
                tool_calls=[OllamaToolCall(name="get_alert_summary", arguments={})]
            )
            for _ in range(3)
        ]
    )
    response = make_agent(fake, analyst_max_tool_rounds=2).chat(
        db_session,
        AnalystChatRequest(message="Resume las alertas."),
    )
    assert response.answer == TOOL_LIMIT_MESSAGE
    assert response.tool_rounds == 2
    assert len(response.tool_calls) == 2


def test_agent_validates_history_limit(db_session: Session) -> None:
    fake = FakeLLMClient([LLMResponse(content="No debería ejecutarse")])
    agent = make_agent(fake, analyst_max_history_messages=1)
    request = AnalystChatRequest(
        message="Hola",
        history=[
            {"role": "user", "content": "uno"},
            {"role": "assistant", "content": "dos"},
        ],
    )
    try:
        agent.chat(db_session, request)
    except DomainValidationError as exc:
        assert "ANALYST_MAX_HISTORY_MESSAGES" in exc.message
    else:
        raise AssertionError("Se esperaba DomainValidationError")


def test_agent_enforces_non_causal_risk_language() -> None:
    answer = ProcessAnalystAgent._apply_language_policy(
        "El riesgo alto es debido a estas causas. "
        "El valor es una causa que aumenta el riesgo."
    )
    assert "causa" not in answer.lower()
    assert "riesgo estimado alto" in answer.lower()
    assert "factor asociado" in answer.lower()


def test_agent_grounds_rework_count_in_tool_output(db_session: Session) -> None:
    fake = FakeLLMClient([
        LLMResponse(
            tool_calls=[OllamaToolCall(name="get_deviation_summary", arguments={})]
        ),
        LLMResponse(content="Hay 999 casos con retrabajo BACKTRACK."),
    ])
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Cuántos casos tienen retrabajo?"),
    )
    assert response.answer == (
        "Según las desviaciones registradas, 0 casos tienen retrabajo (tipo REWORK)."
    )


def test_agent_requires_tool_for_specific_system_fact(db_session: Session) -> None:
    fake = FakeLLMClient([LLMResponse(content="Hay 999 desviaciones.")])
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Cuántas desviaciones hay actualmente?"),
    )
    assert response.answer == CONTROLLED_FAILURE
    assert response.evidence == []


def test_agent_requires_tool_for_count_using_domain_code(db_session: Session) -> None:
    fake = FakeLLMClient([LLMResponse(content="Hay 999 STAGE_SKIP.")])
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Cuántos STAGE_SKIP hay actualmente?"),
    )
    assert response.answer == CONTROLLED_FAILURE


def test_prediction_answer_uses_tool_score_and_non_causal_factors() -> None:
    answer = ProcessAnalystAgent._ground_standard_answer(
        "¿Por qué DEMO-00141 tiene riesgo alto?",
        "El score es una probabilidad real y la causa es inventada.",
        {"get_case_prediction": {
            "status": "success",
            "case_code": "DEMO-00141",
            "risk_level": "HIGH",
            "risk_score": 0.999705,
            "decision_threshold": 0.685,
            "prediction_applicable": True,
            "top_factors": [{
                "feature": "numeric__prior_backtrack_count",
                "value": 1,
                "direction": "INCREASES_RISK",
            }],
        }},
    )
    assert "riesgo estimado alto" in answer
    assert "0.9997" in answer
    assert "retrocesos previos" in answer
    assert "probabilidad real calibrada" in answer
    assert "causa" not in answer


def test_prediction_answer_handles_non_applicable_record() -> None:
    answer = ProcessAnalystAgent._ground_standard_answer(
        "¿Qué riesgo tiene DEMO-00001?",
        "Riesgo alto inventado.",
        {"get_case_prediction": {
            "status": "success",
            "case_code": "DEMO-00001",
            "prediction_applicable": False,
            "risk_score": None,
            "reason": "El caso ya finalizó.",
        }},
    )
    assert answer == (
        "La predicción registrada para DEMO-00001 no es aplicable en este estado. "
        "El caso ya finalizó."
    )


def test_case_deviation_answer_uses_only_recorded_items() -> None:
    answer = ProcessAnalystAgent._ground_standard_answer(
        "¿Qué desviaciones tiene DEMO-00089?",
        "Inventé cinco desviaciones.",
        {"get_case_deviations": {
            "status": "success",
            "case_code": "DEMO-00089",
            "total": 1,
            "truncated": False,
            "deviations": [{
                "type": "REWORK",
                "severity": "MEDIUM",
                "stage": "VISIT",
                "description": "Se ingresó dos veces a VISIT.",
            }],
        }},
    )
    assert "1 desviación registrada" in answer
    assert "REWORK (MEDIUM) en VISIT" in answer
    assert "cinco" not in answer


def test_agent_does_not_invent_when_record_is_not_found(db_session: Session) -> None:
    fake = FakeLLMClient([
        LLMResponse(tool_calls=[
            OllamaToolCall(name="get_case", arguments={"case_code": "MISSING-1"})
        ]),
        LLMResponse(content="El caso tiene riesgo alto inventado."),
    ])
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Qué riesgo tiene MISSING-1?"),
    )
    assert response.answer.startswith("No encontré el dato solicitado.")
    assert "inventado" not in response.answer


def test_agent_retries_when_model_changes_explicit_case_code(
    client,
    db_session: Session,
) -> None:
    create_process_mining_data(client)
    fake = FakeLLMClient([
        LLMResponse(tool_calls=[
            OllamaToolCall(name="get_case", arguments={"case_code": "CASE-A"})
        ]),
        LLMResponse(tool_calls=[
            OllamaToolCall(name="get_case", arguments={"case_code": "CASE-C"})
        ]),
        LLMResponse(content="CASE-C existe."),
    ])
    response = make_agent(fake).chat(
        db_session,
        AnalystChatRequest(message="¿Qué información tiene CASE-C?"),
    )
    assert [call.status for call in response.tool_calls] == [
        "invalid_arguments", "success"
    ]
    assert response.answer == "CASE-C existe."
    assert response.evidence[0].case_code == "CASE-C"
