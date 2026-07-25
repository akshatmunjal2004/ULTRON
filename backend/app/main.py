"""Application factory.

`create_app()` rather than a module-level app so tests can build an isolated
instance, and startup work happens in a lifespan handler rather than the
deprecated @app.on_event("startup").
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.init_db import init_db
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.tools.registry import get_registry

logger = get_logger(__name__)

DESCRIPTION = """
A voice-driven AI agent. Groq for reasoning, SQLite for memory, and a small set
of tools the model can call: web search, Python execution, workspace file
access, long-term memory, links and system info.

Endpoints that write, delete or execute require the `X-API-Key` header whenever
`API_KEY` is set on the server.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.LOG_LEVEL)

    problems = settings.check_runtime_requirements()
    if problems:
        for problem in problems:
            logger.error("Configuration problem: %s", problem)
        if settings.is_production:
            sys.exit(1)
        logger.warning("Starting anyway because ENV=%s.", settings.ENV)

    settings.prepare_directories()
    init_db()

    registry = get_registry()
    logger.info(
        "%s %s ready | model=%s | tools=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.LLM_MODEL,
        ", ".join(registry.enabled_names()),
    )
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # Order matters: the outermost middleware is added last, so the request id
    # is set before the rate limiter can log or reject anything.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,  # the app authenticates with a header, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["health"], include_in_schema=False)
    def legacy_health() -> RedirectResponse:
        """Kept so older frontend builds and uptime checks keep working."""
        return RedirectResponse(f"{settings.API_V1_PREFIX}/health", status_code=308)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if not settings.is_production else "disabled",
            "api": settings.API_V1_PREFIX,
        }

    return app


app = create_app()
