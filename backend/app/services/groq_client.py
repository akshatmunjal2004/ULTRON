"""Thin wrapper around the Groq SDK.

Everything that talks to Groq goes through here: one client instance, one
retry/backoff policy, one place that translates provider exceptions into our
own error type.
"""

from __future__ import annotations

import random
import time
from functools import lru_cache
from typing import Any

from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    Groq,
    RateLimitError,
)

from app.core.config import settings
from app.core.errors import UpstreamError
from app.core.logging import get_logger

logger = get_logger(__name__)

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}


@lru_cache(maxsize=1)
def get_client() -> Groq:
    """One shared client. The SDK pools connections internally."""
    if not settings.GROQ_API_KEY:
        raise UpstreamError(
            "GROQ_API_KEY is not configured on the server.",
            status_code=503,
        )
    return Groq(api_key=settings.GROQ_API_KEY, timeout=settings.LLM_TIMEOUT_SECONDS)


def _sleep_for(attempt: int, retry_after: float | None = None) -> float:
    if retry_after:
        return min(retry_after, 10.0)
    return min(2**attempt + random.uniform(0, 0.4), 10.0)


def chat_completion(
    messages: list[dict[str, Any]],
    *,
    tools: list[dict[str, Any]] | None = None,
    stream: bool = False,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """Call Groq with bounded retries on transient failures."""
    client = get_client()
    payload: dict[str, Any] = {
        "model": model or settings.LLM_MODEL,
        "messages": messages,
        "temperature": (
            settings.LLM_TEMPERATURE if temperature is None else temperature
        ),
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    last_error: Exception | None = None
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(**payload)

        except AuthenticationError as exc:
            # Retrying a bad key just wastes the user's time.
            raise UpstreamError(
                "The Groq API key was rejected. Check GROQ_API_KEY in the backend .env.",
                status_code=502,
            ) from exc

        except RateLimitError as exc:
            last_error = exc
            wait = _sleep_for(attempt, _retry_after(exc))
            logger.warning("Groq rate limit, retrying in %.1fs", wait)

        except APIConnectionError as exc:
            last_error = exc
            wait = _sleep_for(attempt)
            logger.warning("Groq connection problem, retrying in %.1fs", wait)

        except APIStatusError as exc:
            if exc.status_code not in RETRYABLE_STATUS:
                raise UpstreamError(
                    f"Groq rejected the request ({exc.status_code}). "
                    "The model name in LLM_MODEL may be wrong or retired."
                ) from exc
            last_error = exc
            wait = _sleep_for(attempt)
            logger.warning("Groq %s, retrying in %.1fs", exc.status_code, wait)

        if attempt < settings.LLM_MAX_RETRIES:
            time.sleep(wait)

    raise UpstreamError(
        "The language model is not responding right now. Try again in a moment."
    ) from last_error


def _retry_after(exc: Exception) -> float | None:
    response = getattr(exc, "response", None)
    header = getattr(response, "headers", {}) or {}
    try:
        return float(header.get("retry-after", ""))
    except (TypeError, ValueError):
        return None


def is_configured() -> bool:
    return bool(settings.GROQ_API_KEY)
