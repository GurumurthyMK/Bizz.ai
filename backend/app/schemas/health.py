"""Pydantic request/response schemas for health endpoints."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    app: str = Field(examples=["Bizz AI API"])
    environment: str = Field(examples=["development"])


class DbHealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    database: str = Field(examples=["connected"])
