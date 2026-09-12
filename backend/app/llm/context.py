"""Structured business context for LLM calls.

Every prompt is built from verified analytics/ML output passed in by the
caller. Builders trim payloads to the fields the model may reference and cap
list lengths, so prompts stay small and cannot smuggle unvetted content.
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are Bizz AI's interpretation layer. You explain and summarize \
structured business analytics computed by deterministic models.

Strict rules:
- Use ONLY the numbers, names, and facts in the provided BUSINESS CONTEXT.
- Never invent metrics, customers, predictions, opportunities, or business events.
- Never recompute or correct the provided numbers; report them as given.
- If the context lacks the information needed to answer, say what is missing \
instead of guessing.
- Keep the answer concise and business-oriented."""

MAX_LIST_ITEMS = 10


def _trim_list(value: Any) -> Any:
    if isinstance(value, list):
        return value[:MAX_LIST_ITEMS]
    return value


def business_context(kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap a verified payload with its kind. Unknown kinds are rejected."""
    if kind not in ("overview", "customer", "segment", "opportunity", "campaign"):
        raise ValueError(f"Unknown business context kind {kind!r}.")
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Business context payload must be a non-empty mapping.")
    trimmed = {key: _trim_list(value) for key, value in payload.items()}
    return {"kind": kind, "data": trimmed}


def overview_context(health: dict[str, Any], trends: list[dict[str, Any]]) -> dict[str, Any]:
    """Verified KPIs plus trend buckets (already structured by the backend)."""
    return business_context("overview", {"health": health, "trends": trends[:6]})


def customer_context(
    profile: dict[str, Any],
    metrics: dict[str, Any],
    predictions: list[dict[str, Any]],
    opportunities: list[dict[str, Any]],
) -> dict[str, Any]:
    profile_kept = (
        {key: profile[key] for key in ("id", "name", "segment") if key in profile}
        if isinstance(profile, dict)
        else {}
    )
    return business_context(
        "customer",
        {
            "profile": profile_kept,
            "metrics": metrics,
            "predictions": predictions,
            "opportunities": opportunities,
        },
    )


def segment_context(summary: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    return business_context("segment", {"summary": summary, "sample_members": members})


def opportunity_context(opportunity: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    return business_context("opportunity", {"opportunity": opportunity, "evidence": evidence})


def render_prompt_block(context: dict[str, Any]) -> str:
    """Render context as the BUSINESS CONTEXT block of a prompt."""
    return "BUSINESS CONTEXT:\n" + json.dumps(context, indent=2, default=str)
