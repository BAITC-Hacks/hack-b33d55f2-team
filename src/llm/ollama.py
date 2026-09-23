"""Minimal Ollama client restricted to the local machine."""

import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

from pydantic import BaseModel, ValidationError

from src.llm.base import LLMProvider, LLMProviderError, StructuredModel

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _open_loopback(request: Request, timeout: float):
    """Open a loopback request without consulting system proxy settings."""
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)


@dataclass(slots=True)
class OllamaProvider(LLMProvider):
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_OLLAMA_URL
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
            raise ValueError("OLLAMA_BASE_URL must use http://127.0.0.1, http://localhost, or http://[::1].")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OLLAMA_BASE_URL must be a plain loopback server URL.")
        self.base_url = self.base_url.rstrip("/")

    def _request(self, path: str, payload: dict[str, Any] | None = None, *, timeout: float | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}", data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with _open_loopback(request, timeout if timeout is not None else self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMProviderError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            if path == "/api/tags":
                message = f"Ollama is unavailable at {self.base_url} ({reason}). Start Ollama locally."
            else:
                message = f"Ollama request to {self.base_url}{path} failed ({reason})."
            raise LLMProviderError(message) from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise LLMProviderError("Ollama returned an unreadable response.") from exc

    def healthcheck(self) -> None:
        tags = self._request("/api/tags", timeout=5.0)
        models = tags.get("models", [])
        if not isinstance(models, list):
            raise LLMProviderError("Ollama returned an invalid model list from /api/tags.")
        installed = {
            value.strip()
            for item in models
            if isinstance(item, dict)
            for key in ("name", "model")
            if isinstance((value := item.get(key)), str) and value.strip()
        }
        if self.model not in installed:
            raise LLMProviderError(
                f"Ollama is running, but model '{self.model}' is not installed. "
                f"Run: ollama pull {self.model}"
            )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        self.healthcheck()
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": response_model.model_json_schema(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0},
        }
        response = self._request("/api/chat", payload, timeout=self.timeout_seconds)
        content = response.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("Ollama returned no structured message content.")
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMProviderError(f"Ollama output did not match the required schema: {exc}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMProviderError("Ollama returned malformed JSON instead of structured output.") from exc
