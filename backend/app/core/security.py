"""
backend/app/core/security.py
----------------------------
Security controls, authentication, and security headers per §12, §13, and Phase 6 Day 1.

Includes:
- verify_internal_api_key: Constant-time X-Internal-Key validation dependency.
- RequestBodyLimitMiddleware: Enforces MAX_REQUEST_BYTES limit (413 Payload Too Large).
- SecurityHeadersMiddleware: Injects secure headers (nosniff, DENY, strict-origin, cache policies).
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings, get_settings
from app.core.errors import build_error_envelope
from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

# Routes explicitly exempt from internal API key authentication
EXEMPT_ROUTES = frozenset(
    {
        "/health/live",
        "/health/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)


def verify_internal_api_key(request: Request) -> None:
    """
    FastAPI dependency validating the X-Internal-Key header using constant-time comparison.
    Required when APP_ENV == 'production' or when INTERNAL_API_KEY is configured.
    Exempts health and documentation endpoints.
    """
    path = request.url.path
    if request.method == "OPTIONS" or path in EXEMPT_ROUTES:
        return

    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    expected_key = settings.INTERNAL_API_KEY
    is_required = settings.APP_ENV == "production" or bool(expected_key)

    if not is_required:
        return

    if not expected_key:
        logger.error("Internal API key enforcement active but key is unset in configuration.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API key is unconfigured on the server",
        )

    provided_key = request.headers.get("X-Internal-Key")
    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        req_id = request_id_ctx.get()
        logger.warning(
            "Unauthorized request to %s: missing or invalid X-Internal-Key (req_id=%s)",
            path,
            req_id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )


class RequestBodyLimitMiddleware:
    """
    ASGI middleware enforcing maximum request body size (MAX_REQUEST_BYTES).
    Returns 413 PAYLOAD_TOO_LARGE if Content-Length or streaming body exceeds the limit.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = 65_536) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 1. Fast-path check via Content-Length header
        content_length_header = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"content-length":
                content_length_header = value
                break

        if content_length_header is not None:
            try:
                content_length = int(content_length_header.decode("latin1"))
                if content_length > self.max_bytes:
                    await self._send_payload_too_large(send, self.max_bytes)
                    return
            except (ValueError, UnicodeDecodeError):
                pass

        # 2. Guard chunked/streaming bodies
        total_received = 0

        async def limited_receive() -> Message:
            nonlocal total_received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                total_received += len(body)
                if total_received > self.max_bytes:
                    raise PayloadTooLargeError(self.max_bytes)
            return message

        try:
            await self.app(scope, limited_receive, send)
        except PayloadTooLargeError as exc:
            await self._send_payload_too_large(send, exc.max_bytes)

    @staticmethod
    async def _send_payload_too_large(send: Send, max_bytes: int) -> None:
        req_id = request_id_ctx.get() or "unknown"
        body = build_error_envelope(
            code="PAYLOAD_TOO_LARGE",
            message=f"Request body size exceeds maximum allowed limit of {max_bytes} bytes",
            request_id=req_id,
            details={"max_request_bytes": max_bytes},
        )
        response = JSONResponse(
            status_code=413,
            content=body,
            headers={"X-Request-ID": req_id},
        )

        async def _empty_receive() -> dict[str, Any]:
            return {"type": "http.request"}

        await response(dict(type="http"), _empty_receive, send)


class PayloadTooLargeError(Exception):
    """Internal sentinel exception for request body exceeding byte cap."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"Request body exceeds {max_bytes} bytes")
        self.max_bytes = max_bytes


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware injecting essential HTTP security headers per §12 and §13.
    Enforces MIME sniffing protection, frame sandboxing, referrer policy, and cache defaults.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        response: Response = await call_next(request)

        # Standard browser protection headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Safe caching defaults if not already explicitly assigned by route
        if "Cache-Control" not in response.headers:
            path = request.url.path
            if path.startswith("/api/v1/assistant/"):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            elif path.startswith(("/api/v1/analytics/", "/api/v1/dashboard/")):
                response.headers["Cache-Control"] = "private, max-age=60"
            elif path.startswith("/api/v1/complaints/"):
                response.headers["Cache-Control"] = "no-cache"

        return response
