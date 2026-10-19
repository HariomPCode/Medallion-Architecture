"""
backend/app/core/ratelimit.py
-----------------------------
Rate limiting support using slowapi per §12, §13, and Phase 6 Day 1.

Configures:
- Client IP resolution honoring X-Forwarded-For from the Next.js BFF proxy.
- Global Limiter instance configured with default rate limit (120/minute).
- Route-specific limit strings for export (10/hour) and AI assistant (10/minute).
- Sanitized 429 RATE_LIMITED exception handler injecting Retry-After headers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import Settings, get_settings
from app.core.errors import build_error_envelope
from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

# Cached active settings configured on the app instance
_active_settings: Settings | None = None


def set_active_settings(settings: Settings) -> None:
    """Sets the active configuration for rate limit evaluation."""
    global _active_settings
    _active_settings = settings


def get_client_ip(request: Request) -> str:
    """
    Extracts the originating client IP.
    Prioritizes the first IP in X-Forwarded-For (injected by BFF proxy), falling back to client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        first_ip = forwarded.split(",")[0].strip()
        if first_ip:
            return first_ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def get_default_limit() -> str:
    """Returns configured default rate limit (default: 120/minute)."""
    if _active_settings is not None:
        return _active_settings.RATE_LIMIT_DEFAULT
    return get_settings().RATE_LIMIT_DEFAULT


def get_export_limit() -> str:
    """Returns configured export rate limit (default: 10/hour)."""
    if _active_settings is not None:
        return _active_settings.RATE_LIMIT_EXPORT
    return get_settings().RATE_LIMIT_EXPORT


def get_ai_limit() -> str:
    """Returns configured AI assistant chat rate limit (default: 10/minute)."""
    if _active_settings is not None:
        return _active_settings.RATE_LIMIT_AI
    return get_settings().RATE_LIMIT_AI


# Shared slowapi limiter instance with default limits applied to non-exempt endpoints
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[get_default_limit()],
    headers_enabled=True,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Authoritative exception handler for slowapi RateLimitExceeded (HTTP 429).
    Injects Retry-After header and standard error envelope.
    """
    req_id = request_id_ctx.get() or "unknown"
    retry_after = 60
    limit_obj: Any = getattr(exc, "limit", None)
    if limit_obj is not None:
        inner = getattr(limit_obj, "limit", None)
        if inner is not None and hasattr(inner, "get_expiry"):
            try:
                retry_after = int(inner.get_expiry())
            except Exception:
                retry_after = 60

    detail_str = str(exc.detail) if exc.detail else "Rate limit exceeded"
    logger.warning(
        "Rate limit exceeded on %s for client %s: %s (req_id=%s)",
        request.url.path,
        get_client_ip(request),
        detail_str,
        req_id,
    )

    body = build_error_envelope(
        code="RATE_LIMITED",
        message=f"Rate limit exceeded: {detail_str}",
        request_id=req_id,
        details={"rate_limit": detail_str, "retry_after": retry_after},
    )

    headers = {
        "X-Request-ID": req_id,
        "Retry-After": str(retry_after),
    }

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=body,
        headers=headers,
    )


def register_rate_limiting(app: FastAPI) -> None:
    """Registers limiter state, error handler, and middleware onto the FastAPI application."""
    if hasattr(app.state, "settings") and app.state.settings is not None:
        set_active_settings(app.state.settings)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
