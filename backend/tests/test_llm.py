"""LLM tests: selection, grounding, failures, and secret handling.

All provider HTTP traffic runs through httpx.MockTransport — no real
network, no real keys, no real models. The BI contract under test: every
failure surfaces as LLMError (so analytics can degrade), and secrets never
leave the request headers.
"""

import json

import httpx
import pytest

from app.llm import context as ctx
from app.llm.gemini import GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.provider import (
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMTimeoutError,
    get_provider,
)
from app.llm.service import answer_question, generate_insight, summarize

API_KEY = "test-key-123"
SAMPLE_CONTEXT = ctx.overview_context(
    {"revenue": 48210, "orders": 312},
    [{"period": "2026-08", "revenue": 48210}],
)


def gemini_ok_payload(text="Revenue grew on repeat purchases."):
    return {
        "candidates": [
            {"content": {"parts": [{"text": text}]}},
        ]
    }


def capture(handler):
    seen: list[httpx.Request] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    return httpx.MockTransport(wrapped), seen


# --------------------------------------------------------------------------
# Selection
# --------------------------------------------------------------------------


def test_factory_selects_providers() -> None:
    assert isinstance(get_provider("gemini", api_key=API_KEY), GeminiProvider)
    assert isinstance(get_provider("groq", api_key=API_KEY), GroqProvider)


def test_factory_rejects_disabled_and_unknown() -> None:
    with pytest.raises(LLMConfigurationError):
        get_provider("disabled")
    with pytest.raises(LLMConfigurationError):
        get_provider("watson")
    with pytest.raises(LLMError):  # graceful-degradation contract
        get_provider("disabled")


def test_constructors_validate_configuration() -> None:
    with pytest.raises(LLMConfigurationError):
        GeminiProvider(api_key=None, model="m")
    with pytest.raises(LLMConfigurationError):
        GeminiProvider(api_key="", model="m")
    with pytest.raises(LLMConfigurationError):
        GroqProvider(api_key=None, model="m")
    with pytest.raises(LLMConfigurationError):
        GroqProvider(api_key="", model="m")
    with pytest.raises(LLMConfigurationError):
        GeminiProvider(api_key=API_KEY, model="m", timeout_seconds=0)


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------


def test_gemini_success_sends_grounded_request() -> None:
    transport, seen = capture(lambda request: httpx.Response(200, json=gemini_ok_payload()))
    provider = GeminiProvider(api_key=API_KEY, model="gemini-2.0-flash")
    result = provider.generate("Explain.", system="Be brief.", transport=transport)

    assert result.text.startswith("Revenue grew")
    assert result.model == "gemini-2.0-flash"
    assert result.provider == "gemini"
    sent = json.loads(seen[0].content.decode())
    assert sent["contents"][0]["parts"][0]["text"] == "Explain."
    assert sent["systemInstruction"]["parts"][0]["text"] == "Be brief."
    assert seen[0].headers["x-goog-api-key"] == API_KEY
    assert seen[0].url.path.endswith(":generateContent")
    assert "generateContent" in seen[0].url.path


def test_gemini_key_never_in_url_or_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.query == b""
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    transport, seen = capture(handler)
    provider = GeminiProvider(api_key=API_KEY, model="m")
    with pytest.raises(LLMProviderError) as excinfo:
        provider.generate("Hi.", transport=transport)
    assert API_KEY not in str(excinfo.value)
    assert "authentication" in str(excinfo.value).lower()


def test_gemini_server_error_reports_status() -> None:
    transport, _ = capture(lambda request: httpx.Response(500, json={"error": {"message": "boom"}}))
    provider = GeminiProvider(api_key=API_KEY, model="m")
    with pytest.raises(LLMProviderError, match="500"):
        provider.generate("Hi.", transport=transport)


def test_gemini_empty_and_malformed_responses() -> None:
    provider = GeminiProvider(api_key=API_KEY, model="m")
    empty, _ = capture(lambda request: httpx.Response(200, json={"candidates": []}))
    with pytest.raises(LLMInvalidResponseError):
        provider.generate("Hi.", transport=empty)
    broken, _ = capture(lambda request: httpx.Response(200, content=b"not json"))
    with pytest.raises(LLMInvalidResponseError):
        provider.generate("Hi.", transport=broken)


def test_gemini_timeout_and_unreachable() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = GeminiProvider(api_key=API_KEY, model="m", timeout_seconds=1)
    with pytest.raises(LLMTimeoutError):
        provider.generate("Hi.", transport=httpx.MockTransport(timeout))
    with pytest.raises(LLMProviderError, match="unreachable"):
        provider.generate("Hi.", transport=httpx.MockTransport(refused))


# --------------------------------------------------------------------------
# Groq
# --------------------------------------------------------------------------


def groq_ok_payload(text="  Sales are steady.  "):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


def test_groq_success_sends_chat_request() -> None:
    transport, seen = capture(lambda request: httpx.Response(200, json=groq_ok_payload()))
    provider = GroqProvider(api_key=API_KEY, model="llama-3.3-70b-versatile")
    result = provider.generate("Summarize.", system="Be brief.", transport=transport)

    assert result.text == "Sales are steady."
    assert result.model == "llama-3.3-70b-versatile"
    assert result.provider == "groq"
    sent = json.loads(seen[0].content.decode())
    assert sent["model"] == "llama-3.3-70b-versatile"
    assert sent["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Summarize."},
    ]
    assert seen[0].headers["authorization"] == f"Bearer {API_KEY}"
    assert seen[0].url.path.endswith("/chat/completions")


def test_groq_key_never_in_url_or_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.query == b""
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    transport, _ = capture(handler)
    provider = GroqProvider(api_key=API_KEY, model="m")
    with pytest.raises(LLMProviderError) as excinfo:
        provider.generate("Hi.", transport=transport)
    assert API_KEY not in str(excinfo.value)
    assert "authentication" in str(excinfo.value).lower()


def test_groq_rate_limit_and_server_error() -> None:
    limited, _ = capture(lambda request: httpx.Response(429, json={"error": {"message": "slow"}}))
    provider = GroqProvider(api_key=API_KEY, model="m")
    with pytest.raises(LLMProviderError, match="rate limit"):
        provider.generate("Hi.", transport=limited)
    broken, _ = capture(lambda request: httpx.Response(500, json={"error": {"message": "boom"}}))
    with pytest.raises(LLMProviderError, match="500"):
        provider.generate("Hi.", transport=broken)


def test_groq_empty_malformed_timeout_and_unreachable() -> None:
    provider = GroqProvider(api_key=API_KEY, model="m", timeout_seconds=1)
    empty, _ = capture(lambda request: httpx.Response(200, json={"choices": []}))
    with pytest.raises(LLMInvalidResponseError):
        provider.generate("Hi.", transport=empty)
    broken, _ = capture(lambda request: httpx.Response(200, content=b"not json"))
    with pytest.raises(LLMInvalidResponseError):
        provider.generate("Hi.", transport=broken)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMTimeoutError):
        provider.generate("Hi.", transport=httpx.MockTransport(timeout))
    with pytest.raises(LLMProviderError, match="unreachable"):
        provider.generate("Hi.", transport=httpx.MockTransport(refused))


# --------------------------------------------------------------------------
# Structured context
# --------------------------------------------------------------------------


def test_context_builders_validate_and_trim() -> None:
    with pytest.raises(ValueError):
        ctx.business_context("oracle", {"a": 1})
    with pytest.raises(ValueError):
        ctx.business_context("overview", {})
    long_list = [{"i": i} for i in range(50)]
    built = ctx.business_context("overview", {"rows": long_list})
    assert len(built["data"]["rows"]) == 10
    block = ctx.render_prompt_block(built)
    assert "BUSINESS CONTEXT" in block
    assert '"kind": "overview"' in block


def test_overview_and_customer_context_shapes() -> None:
    overview = ctx.overview_context({"revenue": 1}, [{"p": 1}])
    assert overview["kind"] == "overview"
    customer = ctx.customer_context(
        {"id": 7, "name": "N", "segment": "S", "secret": "x"},
        {"orders": 3},
        [{"type": "churn"}],
        [{"score": 1}],
    )
    assert customer["data"]["profile"] == {"id": 7, "name": "N", "segment": "S"}
    assert "secret" not in str(customer["data"]["profile"])


# --------------------------------------------------------------------------
# Service operations
# --------------------------------------------------------------------------


def test_generate_insight_sends_context_and_grounds() -> None:
    transport, seen = capture(lambda request: httpx.Response(200, json=gemini_ok_payload()))
    provider = GeminiProvider(api_key=API_KEY, model="gemini-2.0-flash")
    result = generate_insight(SAMPLE_CONTEXT, provider=provider, transport=transport)

    assert result.provider == "gemini"
    assert result.context_kind == "overview"
    sent = json.loads(seen[0].content.decode())
    prompt_text = sent["contents"][0]["parts"][0]["text"]
    assert "48210" in prompt_text  # the verified metric travels with the call
    system_text = sent["systemInstruction"]["parts"][0]["text"]
    assert "Never invent" in system_text
    assert API_KEY not in prompt_text
    assert API_KEY not in result.text


def test_answer_question_validates_and_asks() -> None:
    with pytest.raises(ValueError):
        answer_question(SAMPLE_CONTEXT, "   ")
    with pytest.raises(ValueError):
        answer_question(SAMPLE_CONTEXT, "x" * 1001)

    transport, seen = capture(
        lambda request: httpx.Response(200, json=groq_ok_payload("Because repeats."))
    )
    provider = GroqProvider(api_key=API_KEY, model="llama-3.3-70b-versatile")
    result = answer_question(
        SAMPLE_CONTEXT, "Why did revenue change?", provider=provider, transport=transport
    )
    assert result.text == "Because repeats."
    messages = json.loads(seen[0].content.decode())["messages"]
    assert any("Why did revenue change?" in message["content"] for message in messages)


def test_summarize_and_empty_result() -> None:
    transport, _ = capture(
        lambda request: httpx.Response(200, json=groq_ok_payload("Steady quarter."))
    )
    provider = GroqProvider(api_key=API_KEY, model="llama-3.3-70b-versatile")
    result = summarize(SAMPLE_CONTEXT, provider=provider, transport=transport)
    assert result.context_kind == "overview"

    blank, _ = capture(lambda request: httpx.Response(200, json=groq_ok_payload("   ")))
    with pytest.raises(LLMError):
        summarize(SAMPLE_CONTEXT, provider=provider, transport=blank)


def test_service_rejects_unbuilt_context() -> None:
    transport, _ = capture(lambda request: httpx.Response(200, json=gemini_ok_payload()))
    provider = GroqProvider(api_key=API_KEY, model="llama-3.3-70b-versatile")
    with pytest.raises(ValueError):
        generate_insight({"raw": "unvetted"}, provider=provider, transport=transport)
