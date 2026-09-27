from app.agents.analyst_agent import ProcessAnalystAgent
from app.agents.tool_registry import get_tool_registry
from app.core.config import Settings
from app.main import app
from app.schemas.analyst import LLMResponse, OllamaToolCall
from app.services.analyst_service import get_process_analyst_agent
from tests.fakes import FakeLLMClient


def test_status_and_chat_work_with_offline_fake_client(client) -> None:
    fake = FakeLLMClient(
        [
            LLMResponse(
                tool_calls=[OllamaToolCall(name="get_alert_summary", arguments={})]
            ),
            LLMResponse(content="No existen alertas registradas."),
        ]
    )
    agent = ProcessAnalystAgent(
        settings=Settings(),
        client=fake,
        registry=get_tool_registry(),
    )
    app.dependency_overrides[get_process_analyst_agent] = lambda: agent
    try:
        status = client.get("/api/v1/analyst/status")
        chat = client.post(
            "/api/v1/analyst/chat",
            json={
                "message": "Resume las alertas.",
                "history": [],
                "context_case_code": None,
            },
        )
    finally:
        app.dependency_overrides.pop(get_process_analyst_agent, None)

    assert status.status_code == 200
    assert status.json() == {
        "enabled": True,
        "configured": True,
        "provider": "ollama",
        "model": agent.settings.ollama_model,
        "available": True,
        "read_only": True,
        "message": "Modelo local disponible.",
    }
    assert chat.status_code == 200
    assert chat.json()["provider"] == "ollama"
    assert chat.json()["tool_calls"][0]["name"] == "get_alert_summary"
    assert chat.json()["evidence"] == [{
        "type": "alert_summary",
        "case_code": None,
        "case_id": None,
        "alert_code": None,
    }]


def test_status_is_safe_when_local_model_is_unavailable(client) -> None:
    agent = ProcessAnalystAgent(
        settings=Settings(),
        client=FakeLLMClient(
            available=False,
            availability_message="Ollama no está disponible.",
        ),
        registry=get_tool_registry(),
    )
    app.dependency_overrides[get_process_analyst_agent] = lambda: agent
    try:
        response = client.get("/api/v1/analyst/status")
    finally:
        app.dependency_overrides.pop(get_process_analyst_agent, None)
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert "API" not in response.text
