"""
backend/tests/api/test_meta.py
------------------------------
API tests for /api/v1/meta/dataset and /api/v1/meta/filters (§13.2 #3 and #4).
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


def test_get_dataset_metadata(client: TestClient) -> None:
    resp = client.get("/api/v1/meta/dataset")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=60"
    data = resp.json()
    assert data["data_origin"] == "fixture"
    assert data["data_status"] in ("fresh", "stale")
    assert data["total_silver_records"] == 40
    assert "row_counts" in data
    assert "coverage" in data
    assert data["coverage"]["start"]
    assert data["coverage"]["end"]
    assert data["schema_version"] == "1.0.0"


def test_get_filters_metadata(client: TestClient) -> None:
    resp = client.get("/api/v1/meta/filters")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=60"
    data = resp.json()
    assert "categories" in data
    assert len(data["categories"]) >= 5
    cat_names = [c["name"] for c in data["categories"]]
    assert "Banking" in cat_names
    assert "submitted_via" in data
    assert "state" in data
    assert "company_response" in data
    assert data["timely"] == ["yes", "no", "unknown"]
    assert "issues" in data
    assert "coverage" in data
