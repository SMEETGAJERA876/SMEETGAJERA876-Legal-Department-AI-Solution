"""HTTP hardening: security headers on every response, per-client rate limits, and refusing to
start an insecure production configuration.

Rate limits are kept in memory, which is right for one API process. With several processes or
machines, move the counters to a shared store (e.g. Redis) — the interface stays the same.
"""

import threading
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    # The API only returns JSON and PDFs; nothing on it may run scripts or be framed.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Resource-Policy": "cross-origin",
}
HSTS = "max-age=31536000; includeSubDomains"


@dataclass(frozen=True)
class Limit:
    name: str
    requests: int
    per_seconds: int


UPLOAD_LIMIT = Limit("upload", 20, 600)  # uploads and corrected copies: 20 per 10 minutes
ASK_LIMIT = Limit("ask", 30, 60)  # questions: 30 per minute
DEFAULT_LIMIT = Limit("default", 300, 60)  # everything else: 300 per minute


def limit_for(method: str, path: str) -> Limit | None:
    if path == "/health":
        return None
    if method == "POST" and (path == "/documents" or path.endswith("/repair")):
        return UPLOAD_LIMIT
    if method == "POST" and path.endswith("/ask"):
        return ASK_LIMIT
    return DEFAULT_LIMIT


class RateLimiter:
    """Sliding-window counters per (client, limit)."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client: str, limit: Limit, now: float | None = None) -> float | None:
        """None if allowed (and counted); otherwise seconds until the next request is allowed."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault((client, limit.name), deque())
            while hits and now - hits[0] >= limit.per_seconds:
                hits.popleft()
            if len(hits) >= limit.requests:
                return limit.per_seconds - (now - hits[0])
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def client_key(request: Request) -> str:
    settings = get_settings()
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def security_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    settings = get_settings()
    limit = limit_for(request.method, request.url.path) if settings.rate_limit_enabled else None
    if limit and request.method != "OPTIONS":
        wait = rate_limiter.check(client_key(request), limit)
        if wait is not None:
            response: Response = JSONResponse(
                status_code=429,
                content={
                    "error": "too_many_requests",
                    "message": "You're going a little fast. Please wait a moment and try again.",
                },
                headers={"Retry-After": str(max(1, round(wait)))},
            )
            _add_headers(response, settings)
            return response
    response = await call_next(request)
    _add_headers(response, settings)
    return response


def _add_headers(response: Response, settings: Settings) -> None:
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if settings.environment == "production":
        response.headers.setdefault("Strict-Transport-Security", HSTS)
    # Document data is private: never store it in shared or browser caches.
    response.headers.setdefault("Cache-Control", "no-store")


class InsecureConfigurationError(RuntimeError):
    pass


def check_production_settings(settings: Settings) -> None:
    """Refuse to start a production server that would expose documents."""
    if settings.environment != "production":
        return
    problems = []
    if settings.auth_mode != "firebase" or not settings.firebase_project_id:
        problems.append("sign-in must be on (AUTH_MODE=firebase and FIREBASE_PROJECT_ID set)")
    if not settings.file_encryption_key:
        problems.append("FILE_ENCRYPTION_KEY must be set (files are encrypted at rest)")
    if any(origin == "*" for origin in settings.cors_origins):
        problems.append("CORS_ORIGINS must list the site's own address, not '*'")
    if not settings.rate_limit_enabled:
        problems.append("RATE_LIMIT_ENABLED must be true")
    if problems:
        raise InsecureConfigurationError("Refusing to start: " + "; ".join(problems))
