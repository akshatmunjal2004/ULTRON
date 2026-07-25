"""API key authentication.

The agent can run code, write files and spend money on tokens, so the mutating
routes sit behind a shared secret. If API_KEY is blank the dependency is a
no-op, which keeps local development frictionless while still failing closed in
production (see Settings.check_runtime_requirements).
"""

from __future__ import annotations

import hmac

from fastapi import Security
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.errors import UnauthorizedError

API_KEY_HEADER = "X-API-Key"

_api_key_scheme = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def require_api_key(provided: str | None = Security(_api_key_scheme)) -> None:
    """FastAPI dependency guarding privileged endpoints."""
    expected = settings.API_KEY
    if not expected:
        return  # auth disabled for local development
    if not provided or not hmac.compare_digest(provided, expected):
        raise UnauthorizedError()
