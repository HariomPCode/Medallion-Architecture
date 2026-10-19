"""
backend/tests/unit/test_errors.py
---------------------------------
Unit tests for standardized error envelopes, exception handling, and log redaction.
"""

import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import build_error_envelope
from app.core.logging import RedactionFilter
from app.main import create_app


def test_build_error_envelope_structure():
    """Verify envelope format matches §13.1 contract."""
    envelope = build_error_envelope(
        code="TEST_ERROR",
        message="Something went wrong",
        request_id="test-req-123",
        details={"key": "val"},
    )
    assert "error" in envelope
    err = envelope["error"]
    assert err["code"] == "TEST_ERROR"
    assert err["message"] == "Something went wrong"
    assert err["request_id"] == "test-req-123"
    assert err["details"] == {"key": "val"}


def test_redaction_filter_removes_secrets():
    """Verify logging RedactionFilter sanitizes credentials."""
    flt = RedactionFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Connecting with key: secret123 and password=pass456",
        args=(),
        exc_info=None,
    )
    flt.filter(record)
    assert "secret123" not in record.msg
    assert "pass456" not in record.msg
    assert "[REDACTED]" in record.msg


@pytest.mark.anyio
async def test_not_found_returns_error_envelope():
    """404 on unknown endpoint returns sanitized envelope with request_id."""
    app = create_app(Settings(APP_ENV="test"))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/unknown/endpoint")
        assert res.status_code == 404
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert "request_id" in data["error"]
        assert "X-Request-ID" in res.headers


@pytest.mark.anyio
async def test_unhandled_exception_returns_sanitized_500():
    """Induced exception returns 500 without leaking stack traces or exception details."""
    app = create_app(Settings(APP_ENV="test"))

    @app.get("/test-induced-failure")
    async def induce_failure():
        raise RuntimeError("Sensitive internal database connection failed: secret_user:secret_pass")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/test-induced-failure")
        assert res.status_code == 500
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_ERROR"
        # Verify sensitive info is NOT leaked in response
        assert "secret_pass" not in res.text
        assert "RuntimeError" not in res.text
        assert "request_id" in data["error"]
