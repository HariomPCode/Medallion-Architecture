"""
backend/tests/api/test_dashboard.py
-----------------------------------
API tests for /api/v1/dashboard/summary (§13.2 #5 and §13.3).
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.data.snapshot import SnapshotManager, set_snapshot_manager
from app.main import create_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    set_snapshot_manager(manager)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    set_snapshot_manager(None)


def test_dashboard_summary_default(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=60"
    data = resp.json()
    assert data["total_complaints"] == 40
    timely = data["timely"]
    # Hand-verified tiny fixture (EXPECTED.md): Yes=32, No=4, Blank=4 -> rated rate = 32 / 36 = 88.89%
    assert timely["yes"] == 32
    assert timely["no"] == 4
    assert timely["unknown"] == 4
    assert timely["rate_denominator"] == 36
    assert timely["rate"] == 88.89
    # Legacy rate: 32 / 40 = 80.0%
    assert timely["rate_all_cases"] == 80.0
    assert data["in_progress_count"] == 4
    assert data["category_count"] == 5
    assert data["coverage"]["start"] == "2017-06-01"
    assert data["coverage"]["end"] == "2023-08-15"


def test_dashboard_summary_with_category_filter(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/summary?category=Banking")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filters_applied"]["category"] == ["Banking"]
    assert data["total_complaints"] == 16
    assert data["category_count"] == 1


def test_dashboard_summary_empty_result_behavior(client: TestClient) -> None:
    # Filter with an impossible date range inside valid boundaries (e.g. 2017-01-01 to 2017-01-02 where data starts June 2017)
    resp = client.get("/api/v1/dashboard/summary?date_from=2017-01-01&date_to=2017-01-02")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_complaints"] == 0
    assert data["timely"]["rate"] is None
    assert data["timely"]["rate_all_cases"] is None
    assert data["timely"]["rate_denominator"] == 0
    assert data["category_count"] == 0


def test_dashboard_summary_unknown_filter_value_returns_422(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/summary?category=NonExistentCategory")
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "allowed_values" in data["error"]["details"]


def test_dashboard_summary_inverted_date_returns_422(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/summary?date_from=2023-01-01&date_to=2022-01-01")
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
