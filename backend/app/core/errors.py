"""
backend/app/core/errors.py
--------------------------
Standardized error envelopes and exception handlers per §13.1.
Never exposes stack traces, server paths, connection strings, or internal errors.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)


def build_error_envelope(
    code: str,
    message: str,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builds the authoritative error envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id or request_id_ctx.get() or "unknown",
        }
    }


class AppError(Exception):
    """Base application exception for domain and business errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DataValidationError(AppError):
    """Raised when data contracts, schemas, or snapshot files fail validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="DATA_VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ValidationException(AppError):
    """Raised when client request parameters, query filters, or payloads fail domain validation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class DataSourceError(AppError):
    """Raised when data cannot be retrieved from storage or local filesystem."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="DATA_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class NotFoundError(AppError):
    """Raised when a specific resource or entity is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handler for domain AppError exceptions."""
    req_id = request_id_ctx.get()
    logger.warning(
        "Application error: %s (code=%s, status=%d)", exc.message, exc.code, exc.status_code
    )
    body = build_error_envelope(
        code=exc.code,
        message=exc.message,
        request_id=req_id,
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers={"X-Request-ID": req_id})


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for Starlette/FastAPI HTTPExceptions."""
    req_id = request_id_ctx.get()
    status_to_code = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        503: "DATA_UNAVAILABLE",
    }
    code = status_to_code.get(exc.status_code, "HTTP_ERROR")
    logger.info("HTTP %d error on %s: %s", exc.status_code, request.url.path, exc.detail)
    body = build_error_envelope(
        code=code,
        message=str(exc.detail),
        request_id=req_id,
    )
    return JSONResponse(status_code=exc.status_code, content=body, headers={"X-Request-ID": req_id})


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler for FastAPI request validation errors (422)."""
    req_id = request_id_ctx.get()
    errors_detail = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors_detail.append(
            {
                "field": field_loc,
                "message": err.get("msg", "Invalid parameter"),
                "type": err.get("type", "value_error"),
            }
        )

    logger.info("Request validation failed on %s: %d issues", request.url.path, len(errors_detail))
    body = build_error_envelope(
        code="VALIDATION_ERROR",
        message="Request parameters failed validation",
        request_id=req_id,
        details={"validation_errors": errors_detail},
    )
    return JSONResponse(
        status_code=422,
        content=body,
        headers={"X-Request-ID": req_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Sanitized handler for uncaught server exceptions (500). Never leaks stack traces."""
    req_id = request_id_ctx.get()
    logger.error("Unhandled server exception on %s: %s", request.url.path, str(exc), exc_info=True)
    body = build_error_envelope(
        code="INTERNAL_ERROR",
        message="An unexpected internal server error occurred. Please quote the request ID.",
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body,
        headers={"X-Request-ID": req_id},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registers all custom exception handlers on the application."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
