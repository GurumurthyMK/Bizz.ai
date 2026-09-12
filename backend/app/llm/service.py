"""Grounded intelligence operations: insight, Q&A, and summarization.

Each operation takes structured context built from verified analytics/ML
output, sends it to the configured provider with the grounding system
prompt, and returns the explanation. All provider failures surface as
``LLMError`` subclasses so BI callers can degrade gracefully — analytics
never depends on these operations succeeding.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.llm.context import SYSTEM_PROMPT, render_prompt_block
from app.llm.provider import LLMInvalidResponseError, LLMProvider, get_provider


class InsightResult(BaseModel):
    """Provider explanation plus provenance. Contains no secrets."""

    text: str = Field(min_length=1)
    model: str
    provider: str
    context_kind: str


def _run(
    provider: LLMProvider,
    task: str,
    context: dict[str, Any],
    transport: httpx.BaseTransport | None = None,
) -> InsightResult:
    if not isinstance(context, dict) or "kind" not in context:
        raise ValueError("Operations require context built by app.llm.context builders.")
    prompt = f"{task}\n\n{render_prompt_block(context)}\n"
    response = provider.generate(prompt, system=SYSTEM_PROMPT, transport=transport)
    text = response.text.strip()
    if not text:
        raise LLMInvalidResponseError("Provider returned an empty explanation.")
    return InsightResult(
        text=text,
        model=response.model,
        provider=response.provider,
        context_kind=str(context["kind"]),
    )


def generate_insight(
    context: dict[str, Any],
    provider: LLMProvider | None = None,
    transport: httpx.BaseTransport | None = None,
) -> InsightResult:
    """Explain what the structured context means for the business."""
    active = provider or get_provider()
    return _run(
        active,
        "Explain what is happening in this data, why it matters, and what "
        "should be investigated. Do not add facts beyond the context.",
        context,
        transport,
    )


def answer_question(
    context: dict[str, Any],
    question: str,
    provider: LLMProvider | None = None,
    transport: httpx.BaseTransport | None = None,
) -> InsightResult:
    """Answer a question using only the structured context."""
    if not question or not question.strip():
        raise ValueError("A non-empty question is required.")
    if len(question) > 1000:
        raise ValueError("Question is too long (max 1000 characters).")
    active = provider or get_provider()
    return _run(
        active,
        f"Answer this business question using only the context below. "
        f"If the context cannot answer it, say so explicitly.\n\nQUESTION: {question.strip()}",
        context,
        transport,
    )


def summarize(
    context: dict[str, Any],
    provider: LLMProvider | None = None,
    transport: httpx.BaseTransport | None = None,
) -> InsightResult:
    """Produce a concise business summary of the structured context."""
    active = provider or get_provider()
    return _run(
        active,
        "Summarize the key points of this data in a few short paragraphs. "
        "Do not add facts beyond the context.",
        context,
        transport,
    )


__all__ = [
    "InsightResult",
    "answer_question",
    "generate_insight",
    "summarize",
]
