"""Gemini provider via the Generative Language REST API.

The API key travels in the ``x-goog-api-key`` header (never in the URL, so
it cannot leak into logs), and is never included in errors or responses.
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

API_BASE = "https://generativelanguage.googleapis.com"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str | None,
        model: str,
        timeout_seconds: float = 30.0,
        api_base: str = API_BASE,
    ) -> None:
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        if not api_key:
            raise LLMConfigurationError("Gemini provider needs GEMINI_API_KEY to be set.")
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> LLMResponse:
        body: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{self._api_base}/v1beta/models/{self.model}:generateContent"
        try:
            with self._client(transport) as client:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": self._api_key},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                f"Gemini model {self.model!r} timed out after {self.timeout_seconds}s."
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Gemini model {self.model!r} is unreachable: {type(exc).__name__}."
            ) from exc
        if response.status_code == 401 or response.status_code == 403:
            raise LLMProviderError(
                "Gemini rejected the request (authentication failed). Check GEMINI_API_KEY."
            )
        if response.status_code != 200:
            raise LLMProviderError(
                f"Gemini request failed with status {response.status_code}: "
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
    parts: list[str] = []
    if isinstance(payload, dict):
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content")
                if not isinstance(content, dict):
                    continue
                for part in content.get("parts", []):
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
    text = "".join(parts).strip()
    if not text:
        raise LLMInvalidResponseError("Gemini returned no usable text (empty candidates).")
    return text[:4000]
