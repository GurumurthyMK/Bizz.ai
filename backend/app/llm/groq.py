"""Groq provider via the OpenAI-compatible chat completions API.

The API key travels in the ``Authorization: Bearer`` header (never in the
URL or body logs), and is never included in errors or responses.
"""

from __future__ import annotations

import httpx

from app.llm.provider import (
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProvider,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    provider_error_details,
)

API_BASE = "https://api.groq.com/openai/v1"


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 30.0,
        api_base: str = API_BASE,
    ) -> None:
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        if not api_key:
            raise LLMConfigurationError("Groq provider needs GROQ_API_KEY to be set.")
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> LLMResponse:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024,
        }
        url = f"{self._api_base}/chat/completions"
        try:
            with self._client(transport) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Groq model {self.model!r} timed out after {self.timeout_seconds}s."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Groq model {self.model!r} is unreachable: {type(exc).__name__}."
            ) from exc
        if response.status_code == 401:
            raise LLMProviderError(
                "Groq rejected the request (authentication failed). Check GROQ_API_KEY."
            )
        if response.status_code == 429:
            raise LLMProviderError(
                "Groq rate limit exceeded. Retry later or use a smaller request."
            )
        if response.status_code != 200:
            raise LLMProviderError(
                f"Groq request failed with status {response.status_code}: "
                f"{provider_error_details(_safe_json(response))}."
            )
        return LLMResponse(
            text=_extract_text(_safe_json(response)),
            model=self.model,
            provider=self.name,
        )


def _safe_json(response: httpx.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return None


def _extract_text(payload: object) -> str:
    text = ""
    if isinstance(payload, dict):
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    text = message["content"]
    text = text.strip()
    if not text:
        raise LLMInvalidResponseError("Groq returned no usable text (empty choices).")
    return text[:4000]
