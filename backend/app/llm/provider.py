"""LLM provider abstraction: one interface, swappable backends.

The LLM is an interpretation layer over deterministic analytics/ML output —
never the source of metrics, customers, predictions, or opportunities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    """Text produced by a provider, with provenance. Never contains secrets."""

    text: str = Field(min_length=1)
    model: str
    provider: str


class LLMError(Exception):
    """Base class: BI callers catch this to degrade gracefully."""


class LLMConfigurationError(LLMError):
    """Missing/invalid configuration, or provider disabled."""


class LLMTimeoutError(LLMError):
    """Provider did not answer within the configured timeout."""


class LLMProviderError(LLMError):
    """Transport failure, rejection, or model-side failure."""


class LLMInvalidResponseError(LLMError):
    """Provider answered, but the payload was unusable."""


class LLMProvider(ABC):
    """Common interface: generate text from a prompt plus optional system prompt."""

    name: str = "base"

    def __init__(self, model: str, timeout_seconds: float = 30.0) -> None:
        if timeout_seconds <= 0:
            raise LLMConfigurationError("timeout must be positive")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> LLMResponse:
        """Generate one completion. ``transport`` exists for tests (MockTransport)."""

    def _client(self, transport: httpx.BaseTransport | None) -> httpx.Client:
        return httpx.Client(transport=transport, timeout=httpx.Timeout(self.timeout_seconds))


def get_provider(
    provider_name: str | None = None,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 30.0,
) -> LLMProvider:
    """Select a provider by name. Unknown or disabled names raise clearly."""
    from app.core.config import settings

    name = (provider_name or settings.llm_provider).strip().lower()
    if name == "gemini":
        from app.llm.gemini import GeminiProvider

        return GeminiProvider(
            api_key=api_key if api_key is not None else settings.gemini_api_key,
            model=model or settings.gemini_model,
            timeout_seconds=timeout_seconds,
        )
    if name == "groq":
        from app.llm.groq import GroqProvider

        return GroqProvider(
            api_key=api_key if api_key is not None else settings.groq_api_key,
            model=model or settings.groq_model,
            timeout_seconds=timeout_seconds,
        )
    if name in ("disabled", "none", ""):
        raise LLMConfigurationError(
            "LLM provider is disabled. Set LLM_PROVIDER=gemini|groq to enable it. "
            "Core analytics work without a provider."
        )
    raise LLMConfigurationError(
        f"Unknown LLM provider {name!r}. Supported: gemini, groq, disabled."
    )


def provider_error_details(payload: Any) -> str:
    """Short, secret-free summary of a provider error payload."""
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error")
        if isinstance(message, dict):
            message = message.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()[:300]
    return "provider request failed"


class DisabledProvider(LLMProvider):
    """Placeholder when no provider is configured. Every call explains why."""

    name = "disabled"

    def __init__(self) -> None:
        self.model = "none"
        self.timeout_seconds = 30.0

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> LLMResponse:
        raise LLMConfigurationError(
            "LLM provider is disabled. Set LLM_PROVIDER=gemini|groq to enable it. "
            "Core analytics work without a provider."
        )
