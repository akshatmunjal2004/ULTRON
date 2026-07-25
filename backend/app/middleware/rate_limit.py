"""A small fixed-window rate limiter.

In-process and per-IP, which is the right size for a single-node personal
assistant. Behind more than one worker or replica, move this to Redis; the
interface stays the same.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import request_id_ctx

EXEMPT_PATHS = {"/health", "/api/v1/health", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int | None = None, window: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit or settings.RATE_LIMIT_REQUESTS
        self.window = window or settings.RATE_LIMIT_WINDOW_SECONDS
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _allowed(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False, int(bucket[0] + self.window - now) + 1
            bucket.append(now)
            # Stop unbounded growth from one-off clients.
            if len(self._hits) > 5000:
                for stale in [k for k, v in self._hits.items() if not v][:1000]:
                    self._hits.pop(stale, None)
            return True, 0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        allowed, retry_after = self._allowed(self._client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": (
                            f"Too many requests. Try again in {retry_after} seconds."
                        ),
                    },
                    "request_id": request_id_ctx.get(),
                },
            )
        return await call_next(request)
