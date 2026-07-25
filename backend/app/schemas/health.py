"""Health/readiness contracts."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
    environment: str


class ReadinessResponse(BaseModel):
    status: str
    database: bool
    llm_configured: bool
    tools_enabled: list[str]
