from app.agents.analyst_agent import ProcessAnalystAgent
from app.agents.llm_client import OllamaLLMClient
from app.agents.tool_registry import get_tool_registry
from app.core.config import get_settings


def get_process_analyst_agent() -> ProcessAnalystAgent:
    settings = get_settings()
    client = OllamaLLMClient(
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.analyst_timeout_seconds,
    )
    return ProcessAnalystAgent(
        settings=settings,
        client=client,
        registry=get_tool_registry(),
    )
