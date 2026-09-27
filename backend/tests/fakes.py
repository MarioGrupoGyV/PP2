from typing import Any

from app.schemas.analyst import LLMResponse


class FakeLLMClient:
    def __init__(
        self,
        responses: list[LLMResponse] | None = None,
        *,
        available: bool = True,
        availability_message: str = "Modelo local disponible.",
    ) -> None:
        self.responses = list(responses or [])
        self.available = available
        self.availability_message = availability_message
        self.requests: list[dict[str, Any]] = []

    def model_available(self, model: str) -> tuple[bool, str]:
        self.requests.append({"operation": "status", "model": model})
        return self.available, self.availability_message

    def chat(self, **kwargs: Any) -> LLMResponse:
        self.requests.append({"operation": "chat", **kwargs})
        if not self.responses:
            raise AssertionError("FakeLLMClient no tiene más respuestas configuradas")
        return self.responses.pop(0)
