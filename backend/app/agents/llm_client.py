import logging
from typing import Any

import httpx

from app.core.exceptions import (
    AnalystExecutionError,
    AnalystTimeoutError,
    AnalystUnavailableError,
)
from app.schemas.analyst import LLMResponse, OllamaToolCall

logger = logging.getLogger(__name__)


class OllamaLLMClient:
    """Cliente mínimo para /api/chat; no conoce la base de datos ni las tools."""

    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    def model_available(self, model: str) -> tuple[bool, str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                body = response.json()
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError):
            return False, "Ollama no está disponible."

        if not isinstance(body, dict) or not isinstance(body.get("models"), list):
            return False, "Ollama devolvió un formato inesperado."

        names = {
            str(item.get("name") or item.get("model"))
            for item in body.get("models", [])
            if isinstance(item, dict)
        }
        if model not in names:
            return False, f"El modelo local {model} no está descargado."
        return True, "Modelo local disponible."

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> LLMResponse:
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                if response.status_code == 404:
                    raise AnalystUnavailableError(
                        f"El modelo local configurado ({model}) no está disponible."
                    )
                response.raise_for_status()
                body = response.json()
        except AnalystUnavailableError:
            raise
        except httpx.TimeoutException as exc:
            raise AnalystTimeoutError("El modelo local excedió el tiempo de espera.") from exc
        except httpx.RequestError as exc:
            logger.warning("Ollama connection failed: %s", type(exc).__name__)
            raise AnalystUnavailableError("Ollama no está disponible.") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("Ollama HTTP error: %s", exc.response.status_code)
            raise AnalystExecutionError("Ollama no pudo completar la consulta.") from exc
        except ValueError as exc:
            raise AnalystExecutionError("Ollama devolvió una respuesta inválida.") from exc

        if not isinstance(body, dict):
            raise AnalystExecutionError("Ollama devolvió un formato inesperado.")
        message = body.get("message")
        if not isinstance(message, dict):
            raise AnalystExecutionError("Ollama devolvió un formato inesperado.")
        raw_calls = message.get("tool_calls") or []
        if not isinstance(raw_calls, list):
            raise AnalystExecutionError("Ollama devolvió un formato inesperado.")
        calls: list[OllamaToolCall] = []
        for raw_call in raw_calls:
            function = raw_call.get("function") if isinstance(raw_call, dict) else None
            if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                calls.append(OllamaToolCall(name="__invalid_tool_call__", arguments={}))
                continue
            calls.append(
                OllamaToolCall(
                    name=function["name"],
                    arguments=function.get("arguments", {}),
                )
            )
        try:
            duration_ms = round(float(body.get("total_duration") or 0) / 1_000_000)
        except (TypeError, ValueError):
            duration_ms = 0
        return LLMResponse(
            content=str(message.get("content") or "").strip(),
            tool_calls=calls,
            duration_ms=duration_ms,
        )
