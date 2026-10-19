"""
backend/tests/api/test_security.py
----------------------------------
Comprehensive security and hardening verification per §12, §13, and Phase 6 Day 1.

Verifies:
- Internal API key authentication (missing -> 401, wrong -> 401, valid -> 200, exempt /health/live).
- CORS preflight behavior for allowed vs denied origins and no credentials.
- Request body size limit middleware (oversize -> 413 PAYLOAD_TOO_LARGE).
- Security headers (nosniff, DENY, strict-origin, cache headers).
- Rate limiter behavior (429 RATE_LIMITED + Retry-After).
- Production settings validation safeguards.
- Error response sanitization (no filesystem paths or server internals leaked).
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_internal_api_key_when_configured():
    """Verify X-Internal-Key enforcement when configured."""
    settings = Settings(
        APP_ENV="test",
        DATA_MODE="fixture",
        INTERNAL_API_KEY="test-internal-secret-key-12345",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        # 1. Unauthenticated request to protected endpoint -> 401
        res = client.get("/api/v1/meta/dataset")
        assert res.status_code == 401
        body = res.json()
        assert body["error"]["code"] == "UNAUTHORIZED"

        # 2. Incorrect key -> 401
        res_bad = client.get(
            "/api/v1/meta/dataset",
            headers={"X-Internal-Key": "wrong-key-value"},
        )
        assert res_bad.status_code == 401
        assert res_bad.json()["error"]["code"] == "UNAUTHORIZED"

        # 3. Valid key -> 200
        res_ok = client.get(
            "/api/v1/meta/dataset",
            headers={"X-Internal-Key": "test-internal-secret-key-12345"},
        )
        assert res_ok.status_code == 200

        # 4. /health/live is exempt from authentication
        res_live = client.get("/health/live")
        assert res_live.status_code == 200
        assert res_live.json()["status"] == "alive"


def test_internal_api_key_unconfigured_in_local():
    """Verify local development works without key when unconfigured."""
    settings = Settings(
        APP_ENV="local",
        DATA_MODE="fixture",
        INTERNAL_API_KEY="",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        res = client.get("/api/v1/meta/dataset")
        assert res.status_code == 200


def test_cors_preflight_allowed_and_denied_origin():
    """Verify CORS preflight accepts allowed origins without credentials and denies unknown origins."""
    settings = Settings(
        APP_ENV="test",
        DATA_MODE="fixture",
        CORS_ALLOW_ORIGINS="http://localhost:3000,https://my-app.vercel.app",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        # 1. Allowed origin preflight
        res_allowed = client.options(
            "/api/v1/meta/dataset",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,X-Request-ID,X-Internal-Key",
            },
        )
        assert res_allowed.status_code == 200
        assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"
        # No credentials allowed
        assert res_allowed.headers.get("access-control-allow-credentials") is None

        # 2. Denied origin preflight
        res_denied = client.options(
            "/api/v1/meta/dataset",
            headers={
                "Origin": "http://malicious-untrusted-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should NOT echo back the untrusted origin
        assert (
            res_denied.headers.get("access-control-allow-origin")
            != "http://malicious-untrusted-site.com"
        )


def test_request_body_size_limit_rejection():
    """Verify requests exceeding MAX_REQUEST_BYTES are rejected with 413 PAYLOAD_TOO_LARGE."""
    settings = Settings(
        APP_ENV="test",
        DATA_MODE="fixture",
        MAX_REQUEST_BYTES=1024,  # 1 KB limit for testing
    )
    app = create_app(settings)

    with TestClient(app) as client:
        # Oversized payload
        oversized_text = "a" * 2048
        res = client.post(
            "/api/v1/assistant/chat",
            json={"question": oversized_text},
        )
        assert res.status_code == 413
        data = res.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"
        assert "exceeds" in data["error"]["message"].lower()


def test_security_headers_injected():
    """Verify browser security headers and cache policies are injected on responses."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)

    with TestClient(app) as client:
        # Test analytics endpoint
        res = client.get("/api/v1/analytics/trends")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "private, max-age=60" in res.headers.get("Cache-Control", "")

        # Test assistant config endpoint
        res_ast = client.get("/api/v1/assistant/config")
        assert res_ast.status_code == 200
        assert "no-store" in res_ast.headers.get("Cache-Control", "")


def test_rate_limiter_trips_and_returns_retry_after():
    """Verify rate limit tripping returns 429 RATE_LIMITED with Retry-After header."""
    settings = Settings(
        APP_ENV="test",
        DATA_MODE="fixture",
        RATE_LIMIT_EXPORT="2/minute",  # Tight export limit for testing
    )
    app = create_app(settings)

    with TestClient(app) as client:
        # Request 1 & 2 succeed
        r1 = client.get("/api/v1/complaints/export")
        assert r1.status_code == 200
        r2 = client.get("/api/v1/complaints/export")
        assert r2.status_code == 200

        # Request 3 trips the 2/minute rate limit
        r3 = client.get("/api/v1/complaints/export")
        assert r3.status_code == 429
        data = r3.json()
        assert data["error"]["code"] == "RATE_LIMITED"
        assert "Retry-After" in r3.headers
        assert r3.headers["Retry-After"].isdigit()
        assert int(r3.headers["Retry-After"]) > 0


def test_production_safeguards_reject_unsafe_values():
    """Verify pydantic settings reject insecure production settings combinations."""
    # 1. Wildcard CORS forbidden
    with pytest.raises(ValueError, match="forbidden in production"):
        Settings(
            APP_ENV="production",
            CORS_ALLOW_ORIGINS="*",
            INTERNAL_API_KEY="a-very-secure-production-key-12345",
        )

    # 2. Missing or weak internal API key forbidden
    with pytest.raises(ValueError, match="INTERNAL_API_KEY must be set"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="short",
        )

    # 3. Connection string auth forbidden in production
    with pytest.raises(ValueError, match="connection_string.*forbidden"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="a-very-secure-production-key-12345",
            AZURE_AUTH_MODE="connection_string",
        )

    # 4. Prompt logging forbidden in production
    with pytest.raises(ValueError, match="LOG_AI_PROMPTS"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="a-very-secure-production-key-12345",
            LOG_AI_PROMPTS=True,
        )

    # 5. Fixture data mode forbidden in production
    with pytest.raises(ValueError, match="DATA_MODE='fixture' is forbidden"):
        Settings(
            APP_ENV="production",
            INTERNAL_API_KEY="a-very-secure-production-key-12345",
            DATA_MODE="fixture",
        )


def test_error_responses_contain_no_filesystem_paths():
    """Verify sanitized error envelopes never leak filesystem paths or server internals."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)

    with TestClient(app) as client:
        # 1. 404 error
        r_404 = client.get("/api/v1/nonexistent-route")
        assert r_404.status_code == 404
        text_404 = r_404.text
        assert "D:\\" not in text_404
        assert "C:\\" not in text_404
        assert "/home/" not in text_404
        assert ".py" not in text_404

        # 2. 422 validation error
        r_422 = client.get("/api/v1/complaints/not-an-id")
        assert r_422.status_code == 422
        text_422 = r_422.text
        assert "D:\\" not in text_422
        assert "C:\\" not in text_422
        assert "/home/" not in text_422
        assert ".py" not in text_422
