"""AI endpoints: grounded explanations over verified backend data.

Every call builds its context server-side from analytics/ML services, then
asks the configured provider to explain it. Provider failures map to 503
with safe messages; the rest of the API is unaffected.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.llm.provider import DisabledProvider, LLMError, LLMProvider, get_provider
from app.llm.service import answer_question, generate_insight, summarize
from app.schemas.ai import AIResponse, AskRequest, InsightRequest, SummarizeRequest
from app.services.ai import build_ai_context

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    dependencies=[Depends(get_current_user)],
)


def get_llm_provider() -> LLMProvider:
    """Override point for tests; production resolves from configuration.

    Never raises: an unconfigured backend yields a DisabledProvider whose
    calls fail as LLMConfigurationError inside the guarded handlers (503).
    """
    from app.llm.provider import LLMConfigurationError

    try:
        return get_provider()
    except LLMConfigurationError:
        return DisabledProvider()


UNAVAILABLE_DETAIL = (
    "AI explanations are unavailable right now. "
    "All metrics and predictions on this page remain verified backend data."
)


def _run_guarded(call) -> AIResponse:  # type: ignore[no-untyped-def]
    try:
        result = call()
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{UNAVAILABLE_DETAIL} ({type(exc).__name__})",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return AIResponse(**result.model_dump())


@router.post("/insight", response_model=AIResponse)
def ai_insight(
    body: InsightRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AIResponse:
    context = build_ai_context(db, body.context.kind, body.context.id)
    return _run_guarded(lambda: generate_insight(context, provider=provider))


@router.post("/ask", response_model=AIResponse)
def ai_ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AIResponse:
    context = build_ai_context(db, body.context.kind, body.context.id)
    return _run_guarded(lambda: answer_question(context, body.question, provider=provider))


@router.post("/summarize", response_model=AIResponse)
def ai_summarize(
    body: SummarizeRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
) -> AIResponse:
    context = build_ai_context(db, body.context.kind, body.context.id)
    return _run_guarded(lambda: summarize(context, provider=provider))
