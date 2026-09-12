"""AI schemas: entity-linked requests, provider answers."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

ContextKind = Literal["overview", "customer", "segment", "opportunity"]


class AIContextRef(BaseModel):
    kind: ContextKind
    id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def id_matches_kind(self) -> "AIContextRef":
        if self.kind == "overview" and self.id is not None:
            raise ValueError("overview context takes no id")
        if self.kind != "overview" and self.id is None:
            raise ValueError(f"{self.kind} context requires an id")
        return self


class InsightRequest(BaseModel):
    context: AIContextRef


class AskRequest(BaseModel):
    context: AIContextRef
    question: str = Field(min_length=1, max_length=1000)


class SummarizeRequest(BaseModel):
    context: AIContextRef


class AIResponse(BaseModel):
    text: str
    model: str
    provider: str
    context_kind: str
