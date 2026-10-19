"""
backend/tests/integration/test_consistency.py
---------------------------------------------
Cross-endpoint analytical consistency suite per §13 and Phase 6 Day 3.

Evaluates 100 seeded pseudo-random filter combinations over the full local snapshot dataset.
Asserts mathematical and logical invariants:
1. Mutual total equality:
   summary.total == sum(by_category.total) == sum(trends.total) == sum(breakdown.items + other) == complaints.total
2. Timely counts consistency:
   summary.timely.yes == sum(by_category.timely_yes)
3. Quality anomalies agreement:
   quality_summary.anomalies.flagged == quality_anomalies.total
4. Assistant tools parity:
   T1 (get_dataset_overview) == /dashboard/summary
   T2 (compare_categories) == /analytics/by-category
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.assistant.tools import execute_tool
from app.core.config import Settings
from app.main import create_app

# Authoritative dimensions from dataset contracts
CATEGORIES = ["Banking", "Collections", "Credit Reporting", "Lending", "Payments"]
SUB_CATEGORIES = [
    "Card Products",
    "Consumer Reporting",
    "Deposit Accounts",
    "Education Lending",
    "Money Movement",
    "Real Estate Lending",
    "Secured Lending",
    "Short-Term Lending",
    "Third-Party Collections",
]
CHANNELS = ["Web", "Phone", "Postal mail", "Referral"]
TIMELY_OPTIONS = ["yes", "no"]
STATES = ["CA", "NY", "TX", "FL", "IL", "PA"]
DATES = [
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2019-06-01", "2022-06-01"),
    (None, None),
]


@pytest.fixture(scope="module")
def local_app_client():
    """Provides a TestClient initialized with full local_snapshot data."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    local_data_dir = repo_root / "backend" / ".local_data"
    if not local_data_dir.exists():
        local_data_dir = repo_root / ".local_data"

    settings = Settings(
        APP_ENV="test",
        DATA_MODE="local_snapshot" if local_data_dir.exists() else "fixture",
        LOCAL_DATA_DIR=str(local_data_dir),
    )
    from app.data.snapshot import SnapshotManager, set_snapshot_manager

    manager = SnapshotManager(settings)
    set_snapshot_manager(manager)
    app = create_app(settings)
    app.state.snapshot_manager = manager

    with TestClient(app) as client:
        yield client, manager.current_snapshot

    set_snapshot_manager(None)


def test_cross_endpoint_consistency_100_seeded_filters(local_app_client):
    """
    AC-6.3: Cross-endpoint consistency holds for 100 seeded random filter sets.
    Verifies total counts, timely counts, and breakdowns mutually agree across all views.
    """
    client, snapshot = local_app_client
    rng = random.Random(42)

    for i in range(100):
        # Generate random filter combination
        params: dict[str, str] = {}
        if rng.random() > 0.5:
            params["category"] = rng.choice(CATEGORIES)
        if rng.random() > 0.6:
            params["sub_category"] = rng.choice(SUB_CATEGORIES)
        if rng.random() > 0.6:
            params["submitted_via"] = rng.choice(CHANNELS)
        if rng.random() > 0.7:
            params["timely"] = rng.choice(TIMELY_OPTIONS)
        if rng.random() > 0.7:
            params["state"] = rng.choice(STATES)
        if rng.random() > 0.6:
            d_from, d_to = rng.choice(DATES)
            if d_from:
                params["date_from"] = d_from
            if d_to:
                params["date_to"] = d_to

        # 1. Summary endpoint
        res_summary = client.get("/api/v1/dashboard/summary", params=params)
        assert res_summary.status_code == 200, (
            f"Summary failed on iteration {i}: {res_summary.text}"
        )
        data_summary = res_summary.json()
        total_summary = data_summary["total_complaints"]
        timely_summary = data_summary["timely"]["yes"]

        # 2. By Category endpoint
        res_cat = client.get("/api/v1/analytics/by-category?group_by=category", params=params)
        assert res_cat.status_code == 200, f"By-category failed on iteration {i}"
        items_cat = res_cat.json()["items"]
        total_cat = sum(c["total"] for c in items_cat)
        timely_cat = sum(c["timely_yes"] for c in items_cat)

        # 3. Trends endpoint (Yearly)
        trends_params = dict(params)
        trends_params["grain"] = "year"
        res_trends = client.get("/api/v1/analytics/trends", params=trends_params)
        assert res_trends.status_code == 200, f"Trends failed on iteration {i}: {res_trends.text}"
        total_trends = sum(p["total"] for p in res_trends.json()["total_series"]["points"])

        # 4. Breakdown endpoint (submitted_via)
        breakdown_params = dict(params)
        breakdown_params["dimension"] = "submitted_via"
        res_breakdown = client.get("/api/v1/analytics/breakdown", params=breakdown_params)
        assert res_breakdown.status_code == 200, (
            f"Breakdown failed on iteration {i}: {res_breakdown.text}"
        )
        total_breakdown = res_breakdown.json()["total"]

        # 5. Complaints list count
        complaints_params = dict(params)
        complaints_params["page"] = "1"
        complaints_params["page_size"] = "1"
        res_complaints = client.get("/api/v1/complaints", params=complaints_params)
        assert res_complaints.status_code == 200, f"Complaints failed on iteration {i}"
        total_complaints = res_complaints.json()["total"]

        # Mutual consistency assertions
        assert total_summary == total_cat, (
            f"Iter {i}: summary ({total_summary}) != cat ({total_cat})"
        )
        assert total_summary == total_trends, (
            f"Iter {i}: summary ({total_summary}) != trends ({total_trends})"
        )
        assert total_summary == total_breakdown, (
            f"Iter {i}: summary ({total_summary}) != breakdown ({total_breakdown})"
        )
        assert total_summary == total_complaints, (
            f"Iter {i}: summary ({total_summary}) != complaints ({total_complaints})"
        )
        assert timely_summary == timely_cat, (
            f"Iter {i}: timely summary ({timely_summary}) != cat ({timely_cat})"
        )


def test_quality_anomalies_consistency(local_app_client):
    """Verify anomaly counts in quality summary match the total in anomalies explorer."""
    client, _ = local_app_client

    res_summary = client.get("/api/v1/quality/summary")
    assert res_summary.status_code == 200
    summary_anomalies = res_summary.json()["anomalies"]["flagged"]

    res_list = client.get("/api/v1/quality/anomalies?page=1&page_size=1")
    assert res_list.status_code == 200
    list_total = res_list.json()["total"]

    assert summary_anomalies == list_total


def test_assistant_tools_parity_with_rest_endpoints(local_app_client):
    """Verify assistant tool outputs exactly match corresponding REST endpoint results."""
    client, snapshot = local_app_client

    # T1 vs /dashboard/summary
    t1_env = execute_tool("get_dataset_overview", {}, snapshot)
    t1_res = t1_env["result"]
    rest_summary = client.get("/api/v1/dashboard/summary").json()
    assert t1_res["total_complaints"] == rest_summary["total_complaints"]
    assert t1_res["timely"]["yes"] == rest_summary["timely"]["yes"]
    assert t1_res["in_progress_count"] == rest_summary["in_progress_count"]

    # T2 vs /analytics/by-category
    t2_env = execute_tool("compare_categories", {"group_by": "category"}, snapshot)
    t2_res = t2_env["result"]
    rest_cat = client.get("/api/v1/analytics/by-category?group_by=category").json()
    assert len(t2_res["items"]) == len(rest_cat["items"])
    assert t2_res["items"][0]["category"] == rest_cat["items"][0]["category"]
    assert t2_res["items"][0]["total"] == rest_cat["items"][0]["total"]
