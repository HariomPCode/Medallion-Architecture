"""
backend/tests/api/test_analytics.py
-----------------------------------
API tests for /api/v1/analytics/by-category, trends, breakdown, and kpis (§13.2 #6–8).
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


# 1. By-Category / Categories Tests
def test_by_category_default(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/by-category")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=60"
    data = resp.json()
    assert data["group_by"] == "category"
    assert data["total"] == 40
    assert len(data["items"]) == 5
    # Sum of item totals equals overall total
    assert sum(item["total"] for item in data["items"]) == 40
    # Items sorted by total descending by default
    totals = [item["total"] for item in data["items"]]
    assert totals == sorted(totals, reverse=True)


def test_categories_alias_matches_by_category(client: TestClient) -> None:
    resp1 = client.get("/api/v1/analytics/by-category")
    resp2 = client.get("/api/v1/analytics/categories")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json() == resp2.json()


def test_by_category_group_by_sub_category(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/by-category?group_by=sub_category")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_by"] == "sub_category"
    assert sum(item["total"] for item in data["items"]) == 40
    for item in data["items"]:
        assert item["sub_category"] is not None


def test_by_category_sort_by_name_asc(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/by-category?sort=name&order=asc")
    assert resp.status_code == 200
    data = resp.json()
    names = [item["category"] for item in data["items"]]
    assert names == sorted(names)


# 2. Trends Tests
def test_trends_year_grain(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/trends?grain=year")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "private, max-age=60"
    data = resp.json()
    assert data["grain"] == "year"
    assert data["group_by"] == "none"
    points = data["total_series"]["points"]
    # Sum of year points equals total
    assert sum(p["total"] for p in points) == 40
    # First year (2017) and last year (2023) are partial in fixture dataset (coverage June 2017 to Aug 2023)
    p_2017 = next(p for p in points if p["period"] == "2017")
    p_2023 = next(p for p in points if p["period"] == "2023")
    assert p_2017["is_partial"] is True
    assert p_2023["is_partial"] is True
    assert p_2017["yoy_change_pct"] is None
    assert p_2023["yoy_change_pct"] is None


def test_trends_by_category(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/trends?grain=year&group_by=category")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_by"] == "category"
    assert len(data["series"]) == 5
    # Sum across all category series for each period equals total_series points
    for idx, total_pt in enumerate(data["total_series"]["points"]):
        cat_sum = sum(s["points"][idx]["total"] for s in data["series"])
        assert cat_sum == total_pt["total"]


def test_trends_month_grain(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/trends?grain=month")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grain"] == "month"
    points = data["total_series"]["points"]
    assert sum(p["total"] for p in points) == 40


# 3. Breakdown Tests
def test_breakdown_submitted_via(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/breakdown?dimension=submitted_via&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dimension"] == "submitted_via"
    assert data["total"] == 40
    assert len(data["items"]) <= 3  # Top 2 + Other
    # Sum of items equals total
    assert sum(item["total"] for item in data["items"]) == 40


def test_breakdown_missing_dimension_returns_422(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/breakdown")
    assert resp.status_code == 422


def test_breakdown_invalid_dimension_returns_422(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/breakdown?dimension=invalid_dim")
    assert resp.status_code == 422


# 4. KPIs Test
def test_kpis_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/analytics/kpis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_complaints"] == 40
    assert data["timely"]["rate"] == 88.89
    assert data["timely"]["rate_all_cases"] == 80.0
