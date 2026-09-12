"""LLM provider abstraction layer (Phase 4B-1: backend only, no UI)."""

from app.llm import context, service
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.provider import (
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    get_provider,
)
from app.llm.service import InsightResult, answer_question, generate_insight, summarize

__all__ = [
    "GeminiProvider",
    "InsightResult",
    "LLMConfigurationError",
    "LLMError",
    "LLMInvalidResponseError",
    "LLMProvider",
    "LLMProviderError",
    "LLMResponse",
    "LLMTimeoutError",
    "answer_question",
    "context",
    "generate_insight",
    "get_provider",
    "GroqProvider",
    "service",
    "summarize",
]
