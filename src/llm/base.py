"""Provider abstraction for structured, locally hosted language models."""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class LLMProviderError(RuntimeError):
    """Safe, user-facing failure from a local LLM provider."""


class LLMProvider(ABC):
    @abstractmethod
    def healthcheck(self) -> None:
        """Raise LLMProviderError when the local provider cannot serve requests."""

    @abstractmethod
    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModel],
    ) -> StructuredModel:
        """Generate and validate a response against a Pydantic schema."""
