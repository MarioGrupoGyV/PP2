from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AnalystHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content no puede estar vacío")
        return normalized


class AnalystChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[AnalystHistoryMessage] = Field(default_factory=list, max_length=20)
    context_case_code: str | None = Field(default=None, max_length=100)

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message no puede estar vacío")
        return normalized

    @field_validator("context_case_code")
    @classmethod
    def normalize_case_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class AnalystToolTrace(BaseModel):
    name: str
    status: Literal["success", "not_found", "invalid_arguments", "error"]
    duration_ms: int


class AnalystEvidence(BaseModel):
    type: str
    case_code: str | None = None
    case_id: UUID | None = None
    alert_code: str | None = None


class AnalystChatResponse(BaseModel):
    answer: str
    provider: Literal["ollama"] = "ollama"
    model: str
    read_only: bool = True
    tool_calls: list[AnalystToolTrace] = Field(default_factory=list)
    evidence: list[AnalystEvidence] = Field(default_factory=list)
    duration_ms: int
    tool_rounds: int


class AnalystStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    provider: Literal["ollama"] = "ollama"
    model: str
    available: bool
    read_only: bool = True
    message: str


class OllamaMessage(BaseModel):
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class OllamaToolCall(BaseModel):
    name: str
    arguments: Any


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[OllamaToolCall] = Field(default_factory=list)
    duration_ms: int = 0
