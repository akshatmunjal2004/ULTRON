"""Liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import Tools
from app.core.config import settings
from app.db.session import healthcheck
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services import groq_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    return HealthResponse(
        status="online",
        version=settings.APP_VERSION,
        model=settings.LLM_MODEL,
        environment=settings.ENV,
    )


@router.get("/ready", response_model=ReadinessResponse, summary="Readiness probe")
def ready(tools: Tools) -> ReadinessResponse:
    db_ok = healthcheck()
    llm_ok = groq_client.is_configured()
    return ReadinessResponse(
        status="ready" if (db_ok and llm_ok) else "degraded",
        database=db_ok,
        llm_configured=llm_ok,
        tools_enabled=tools.enabled_names(),
    )
