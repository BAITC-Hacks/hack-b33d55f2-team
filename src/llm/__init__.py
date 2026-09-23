"""Local-only LLM provider boundary."""

from src.llm.base import LLMProvider, LLMProviderError
from src.llm.ollama import OllamaProvider

__all__ = ["LLMProvider", "LLMProviderError", "OllamaProvider"]
