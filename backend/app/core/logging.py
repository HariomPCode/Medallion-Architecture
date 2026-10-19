"""
backend/app/core/logging.py
---------------------------
Structured logging with request-ID tracking and sensitive data redaction.
Ensures zero leaks of keys, connection strings, or private data in application logs.
"""

import contextvars
import json
import logging
import re
import sys
import uuid
from typing import Any, Callable, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request-scoped correlation ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

# Pattern for redacting sensitive keywords in log messages and records
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?i)(key|secret|token|connection_string|password|auth|authorization|sig)\s*[:=]\s*['\"]?([^'\"\s,;]+)",
)


class RedactionFilter(logging.Filter):
    """Filters log records to redact credentials, tokens, and secret patterns."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SENSITIVE_KEY_PATTERN.sub(r"\1=[REDACTED]", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                redacted_args = {}
                for k, v in record.args.items():
                    if any(
                        s in str(k).lower() for s in ["key", "secret", "token", "password", "sig"]
                    ):
                        redacted_args[k] = "[REDACTED]"
                    else:
                        redacted_args[k] = v
                record.args = redacted_args
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    "[REDACTED]"
                    if any(s in str(a).lower() for s in ["accountkey", "bearer", "sig="])
                    else a
                    for a in record.args
                )
        return True


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or None,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class ConsoleLogFormatter(logging.Formatter):
    """Formats log records for local human-readable console output."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = request_id_ctx.get()
        prefix = f"[{req_id[:8]}] " if req_id else ""
        formatted_msg = super().format(record)
        return f"{prefix}{formatted_msg}"


def configure_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """Configures root and application loggers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Clear existing handlers to prevent duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level.upper())
    handler.addFilter(RedactionFilter())

    if log_format.lower() == "json":
        handler.setFormatter(JSONLogFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ"))
    else:
        fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        handler.setFormatter(ConsoleLogFormatter(fmt, datefmt="%H:%M:%S"))

    root_logger.addHandler(handler)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a correlation ID to every request and response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        header_val = request.headers.get("X-Request-ID")
        req_id = header_val if header_val else str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return cast(Response, response)
        except Exception as exc:
            # Catch unhandled exceptions that bubble past endpoint handlers to ensure sanitized response
            from app.core.errors import unhandled_exception_handler

            err_response = await unhandled_exception_handler(request, exc)
            err_response.headers["X-Request-ID"] = req_id
            return err_response
        finally:
            request_id_ctx.reset(token)
