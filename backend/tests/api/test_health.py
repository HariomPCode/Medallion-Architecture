"""
backend/tests/api/test_health.py
--------------------------------
Tests for /health/live and /health/ready endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.mark.anyio
async def test_health_live_endpoint():
    """Verify /health/live returns 200, app_env, and X-Request-ID header."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["app_env"] == "test"
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] == data["request_id"]


@pytest.mark.anyio
async def test_request_id_propagation():
    """Verify incoming X-Request-ID is honored and returned in headers."""
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    app = create_app(settings)

    custom_id = "test-custom-request-id-12345"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id
        assert response.json()["request_id"] == custom_id
