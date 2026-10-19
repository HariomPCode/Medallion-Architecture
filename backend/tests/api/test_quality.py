"""
backend/tests/api/test_quality.py
---------------------------------
API integration tests for Data Quality Center endpoints (§13.2 #12, #13).
Tests summary payload, decomposed dimensions, audit limitations, model metadata,
and paginated annotated anomaly listings.
"""

import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.data.snapshot import SnapshotManager, set_snapshot_manager
from app.main import create_app


@pytest.fixture
def client():
    settings = Settings(APP_ENV="test", DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    set_snapshot_manager(manager)
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    set_snapshot_manager(None)


def test_quality_summary_success(client):
    """GET /api/v1/quality/summary returns composite score, 5 dimensions, and audit caveats."""
    resp = client.get("/api/v1/quality/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert "overall_quality_score" in data
    assert "status" in data
    assert "total_records" in data
    assert "dimensions" in data
    assert "anomalies" in data
    assert "model" in data
    assert "timestamps" in data
    assert "limitations" in data

    # Decomposed dimensions check
    dims = data["dimensions"]
    assert len(dims) == 5
    dim_ids = [d["id"] for d in dims]
    assert dim_ids == ["completeness", "validity", "consistency", "uniqueness", "ml_normality"]

    # Model metadata check
    model = data["model"]
    assert model["type"] == "IsolationForest"
    assert model["contamination"] == 0.05
    assert model["source"] in ("run_metadata", "notebook_constant")

    # Limitations check (§6 A-05..A-08)
    assert len(data["limitations"]) >= 4
    assert any("ML Normality" in lim for lim in data["limitations"])


def test_quality_anomalies_success(client):
    """GET /api/v1/quality/anomalies returns paginated anomaly records with annotations."""
    resp = client.get("/api/v1/quality/anomalies", params={"page_size": 10})
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "total_pages" in data

    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10

    if data["items"]:
        item = data["items"][0]
        assert "complaint_id" in item
        assert "anomaly_score" in item
        assert "is_anomaly" in item
        assert "annotations" in item
        ann = item["annotations"]
        assert "open_case" in ann
        assert "long_routing_delay" in ann
        assert "timely_no" in ann
        assert item["annotations_note"] == "Observations, not model explanations"


def test_quality_anomalies_page_size_limit(client):
    """page_size > 100 returns 422."""
    resp = client.get("/api/v1/quality/anomalies", params={"page_size": 101})
    assert resp.status_code == 422


def test_quality_anomalies_unknown_param_returns_422(client):
    """Unknown query parameter returns 422."""
    resp = client.get("/api/v1/quality/anomalies", params={"bogus_param": "xyz"})
    assert resp.status_code == 422


def test_quality_anomalies_invalid_category_returns_422(client):
    """Invalid category filter value returns 422 with allowed values."""
    resp = client.get("/api/v1/quality/anomalies", params={"category": "NonExistentCategory"})
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "allowed_values" in err["details"]
