from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.analyst import LLMResponse


class LLMClient(Protocol):
    def model_available(self, model: str) -> tuple[bool, str]: ...

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> LLMResponse: ...


@dataclass(slots=True)
class ToolPayload:
    data: dict[str, Any]
    status: str = "success"
    evidence: list[dict[str, Any]] = field(default_factory=list)


ToolHandler = Callable[[Session, BaseModel, Settings], ToolPayload]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: ToolHandler


@dataclass(slots=True)
class ToolExecution:
    output: dict[str, Any]
    name: str
    status: str
    duration_ms: int
    evidence: list[dict[str, Any]] = field(default_factory=list)
