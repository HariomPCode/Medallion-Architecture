"""
backend/tests/api/test_complaints.py
------------------------------------
API integration tests for Complaint Explorer and Export endpoints (§13.2 #9, #10, #11).
Tests HTTP contracts, filter parameter validation, query ID lookup, error handling,
streaming CSV export, and cross-endpoint consistency with dashboard summary (AC-4.3).
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


def test_list_complaints_default(client):
    """GET /api/v1/complaints returns 200 with paginated items and envelope."""
    resp = client.get("/api/v1/complaints")
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "total_pages" in data

    assert data["page"] == 1
    assert data["page_size"] == 25
    assert data["total"] > 0
    assert len(data["items"]) <= 25

    # Check item field whitelist (§13.3)
    if data["items"]:
        first = data["items"][0]
        expected_keys = {
            "complaint_id",
            "date_submitted",
            "category",
            "sub_category",
            "product",
            "issue",
            "submitted_via",
            "state",
            "company_response",
            "timely_response",
            "is_anomaly",
        }
        assert set(first.keys()) == expected_keys


def test_list_complaints_with_filters(client):
    """GET /api/v1/complaints respects category and submitted_via filters."""
    # First get allowed filters
    meta_resp = client.get("/api/v1/meta/filters")
    assert meta_resp.status_code == 200
    categories = meta_resp.json()["categories"]
    if not categories:
        pytest.skip("No categories in fixture")

    cat_name = categories[0]["name"]
    resp = client.get("/api/v1/complaints", params={"category": cat_name})
    assert resp.status_code == 200
    data = resp.json()

    for item in data["items"]:
        assert item["category"] == cat_name


def test_list_complaints_q_filter(client):
    """'q' parameter finds exact Complaint_ID; invalid 'q' returns 422."""
    list_resp = client.get("/api/v1/complaints?page_size=1")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No items in fixture")

    target_id = items[0]["complaint_id"]

    # Valid ID lookup
    resp = client.get("/api/v1/complaints", params={"q": str(target_id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["complaint_id"] == target_id

    # Non-existent valid numeric ID returns 0 matches
    resp_empty = client.get("/api/v1/complaints", params={"q": "999999999"})
    assert resp_empty.status_code == 200
    assert resp_empty.json()["total"] == 0
    assert resp_empty.json()["items"] == []

    # Non-numeric 'q' returns 422
    resp_inv = client.get("/api/v1/complaints", params={"q": "abc"})
    assert resp_inv.status_code == 422
    assert resp_inv.json()["error"]["code"] == "VALIDATION_ERROR"

    # Oversized 'q' (> 12 digits) returns 422
    resp_too_long = client.get("/api/v1/complaints", params={"q": "1234567890123"})
    assert resp_too_long.status_code == 422


def test_list_complaints_page_size_limit(client):
    """Page size > 100 returns 422 (AC-4.1)."""
    resp = client.get("/api/v1/complaints", params={"page_size": 101})
    assert resp.status_code == 422


def test_list_complaints_unknown_param_returns_422(client):
    """Unknown query parameter returns 422."""
    resp = client.get("/api/v1/complaints", params={"unknown_field": "val"})
    assert resp.status_code == 422


def test_complaint_detail_success_and_not_found(client):
    """GET /api/v1/complaints/{id} returns full detail or 404."""
    list_resp = client.get("/api/v1/complaints?page_size=1")
    items = list_resp.json()["items"]
    if not items:
        pytest.skip("No items in fixture")

    target_id = items[0]["complaint_id"]

    resp = client.get(f"/api/v1/complaints/{target_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["complaint_id"] == target_id
    assert "days_submitted_to_received" in data
    assert "sub_product" in data
    assert "sub_issue" in data
    assert "company_public_response" in data

    # 404 for missing ID
    resp_404 = client.get("/api/v1/complaints/999999999")
    assert resp_404.status_code == 404
    assert resp_404.json()["error"]["code"] == "NOT_FOUND"

    # 422 for non-integer ID
    resp_422 = client.get("/api/v1/complaints/non-numeric")
    assert resp_422.status_code == 422


def test_export_complaints_csv(client):
    """GET /api/v1/complaints/export streams CSV with proper headers and row count."""
    resp = client.get("/api/v1/complaints/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Content-Disposition" in resp.headers
    assert "X-Export-Truncated" in resp.headers
    assert "X-Export-Row-Count" in resp.headers

    lines = [line for line in resp.text.split("\r\n") if line.strip()]
    assert len(lines) >= 2  # header + at least 1 record
    header = lines[0]
    assert "complaint_id" in header
    assert "date_submitted" in header
    assert "category" in header
    assert "timely_response" in header


def test_export_complaints_matches_filtered_list(client):
    """CSV export row count matches complaint list count under identical filters."""
    meta_resp = client.get("/api/v1/meta/filters")
    categories = meta_resp.json()["categories"]
    if not categories:
        pytest.skip("No categories in fixture")

    cat_name = categories[0]["name"]
    params = {"category": cat_name}

    list_resp = client.get("/api/v1/complaints", params=params)
    assert list_resp.status_code == 200
    expected_total = list_resp.json()["total"]

    export_resp = client.get("/api/v1/complaints/export", params=params)
    assert export_resp.status_code == 200
    assert int(export_resp.headers["X-Export-Row-Count"]) == expected_total


def test_complaints_total_equals_dashboard_summary_total(client):
    """AC-4.3: total in complaints list equals total_complaints in dashboard summary."""
    summary_resp = client.get("/api/v1/dashboard/summary")
    assert summary_resp.status_code == 200
    summary_total = summary_resp.json()["total_complaints"]

    complaints_resp = client.get("/api/v1/complaints")
    assert complaints_resp.status_code == 200
    list_total = complaints_resp.json()["total"]

    assert list_total == summary_total
