"""
backend/tests/integration/test_reconciliation.py
------------------------------------------------
Integration test suite for Appendix B Golden Values reconciliation
and cross-endpoint multi-dimensional consistency (§1051, §1063, §1075).
"""

import os
import random
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(scope="module")
def local_snapshot_client() -> Any:
    """Provides a TestClient initialized with the local snapshot (62,516 rows)."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    local_data_dir = os.path.join(repo_root, "backend", ".local_data")
    if not os.path.exists(local_data_dir):
        pytest.skip(
            "backend/.local_data directory does not exist. Run scripts/build_local_snapshot.py first."
        )

    settings = Settings(
        APP_ENV="test",
        DATA_MODE="local_snapshot",
        LOCAL_DATA_DIR=local_data_dir,
    )
    from app.data.snapshot import SnapshotManager, set_snapshot_manager

    manager = SnapshotManager(settings)
    set_snapshot_manager(manager)
    app = create_app(settings)
    with TestClient(app) as client:
        yield client
    set_snapshot_manager(None)


# 1. Full Baseline Golden Values Verification (Appendix B)
def test_dashboard_summary_matches_appendix_b(local_snapshot_client: TestClient) -> None:
    resp = local_snapshot_client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Totals
    assert data["total_complaints"] == 62516
    timely = data["timely"]
    assert timely["yes"] == 58619
    assert timely["no"] == 2403
    assert timely["unknown"] == 1494
    assert timely["rate_denominator"] == 61022
    assert timely["rate"] == 96.06  # Primary rate M-03
    assert timely["rate_all_cases"] == 93.77  # Legacy rate M-04

    assert data["in_progress_count"] == 1494
    assert data["category_count"] == 5
    assert data["sub_category_count"] == 9
    assert data["coverage"]["start"] == "2017-05-01"
    assert data["coverage"]["end"] == "2023-08-28"


def test_category_analytics_matches_appendix_b(local_snapshot_client: TestClient) -> None:
    # 1. Category level
    resp = local_snapshot_client.get("/api/v1/analytics/by-category?group_by=category")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 62516

    expected_categories = {
        "Banking": 24814,
        "Payments": 19650,
        "Credit Reporting": 7710,
        "Lending": 7606,
        "Collections": 2736,
    }
    cat_items = {it["category"]: it["total"] for it in data["items"]}
    assert cat_items == expected_categories

    # 2. Sub-category level
    resp_sub = local_snapshot_client.get("/api/v1/analytics/by-category?group_by=sub_category")
    assert resp_sub.status_code == 200
    data_sub = resp_sub.json()

    expected_sub_categories = {
        "Deposit Accounts": (24814, 93.6, 96.4),
        "Card Products": (16197, 93.2, 95.6),
        "Consumer Reporting": (7710, 91.4, 93.7),
        "Real Estate Lending": (6601, 99.1, 99.8),
        "Money Movement": (3453, 93.9, 95.9),
        "Third-Party Collections": (2736, 91.9, 93.6),
        "Secured Lending": (633, 92.3, 94.7),
        "Short-Term Lending": (333, 96.4, 97.0),
        "Education Lending": (39, 100.0, 100.0),
    }

    for it in data_sub["items"]:
        sub_name = it["sub_category"]
        assert sub_name in expected_sub_categories, f"Unexpected sub-category {sub_name}"
        exp_total, exp_legacy, exp_rated = expected_sub_categories[sub_name]
        assert it["total"] == exp_total
        # Match to 0.1% per plan §1051
        assert abs(it["timely_rate_all_cases"] - exp_legacy) <= 0.1
        assert abs(it["timely_rate"] - exp_rated) <= 0.1


def test_trends_analytics_matches_appendix_b(local_snapshot_client: TestClient) -> None:
    resp = local_snapshot_client.get("/api/v1/analytics/trends?grain=year")
    assert resp.status_code == 200
    data = resp.json()

    expected_years = {
        "2017": (5394, True, None),
        "2018": (7872, False, None),
        "2019": (7075, False, -10.12),
        "2020": (8942, False, 26.39),
        "2021": (11149, False, 24.68),
        "2022": (12953, False, 16.18),
        "2023": (9131, True, None),
    }

    points = {
        p["period"]: (p["total"], p["is_partial"], p["yoy_change_pct"])
        for p in data["total_series"]["points"]
    }
    assert points == expected_years


# 2. Cross-Endpoint Consistency Tests Across Random Filter Combinations (§1051, §1066)
def test_cross_endpoint_consistency_property_test(local_snapshot_client: TestClient) -> None:
    """
    Evaluates 20 seeded random filter sets to guarantee that:
    summary.total == sum(by-category.items) == sum(trends.points) == sum(breakdown.items).
    """
    random.seed(42)

    categories_pool = ["Banking", "Payments", "Credit Reporting", "Lending", "Collections"]
    channels_pool = ["Web", "Phone", "Postal mail", "Referral", "Email", "Fax"]
    states_pool = ["CA", "NY", "FL", "TX", "GA", "IL"]
    years_pool = ["2018", "2019", "2020", "2021", "2022"]

    for _ in range(20):
        params: list[tuple[str, str]] = []

        # Random category subset
        if random.random() > 0.4:
            sampled_cats = random.sample(categories_pool, k=random.randint(1, 3))
            for c in sampled_cats:
                params.append(("category", c))

        # Random channel
        if random.random() > 0.5:
            sampled_chans = random.sample(channels_pool, k=random.randint(1, 2))
            for ch in sampled_chans:
                params.append(("submitted_via", ch))

        # Random state
        if random.random() > 0.5:
            sampled_states = random.sample(states_pool, k=random.randint(1, 3))
            for s in sampled_states:
                params.append(("state", s))

        # Random year bounds
        if random.random() > 0.6:
            y_start = random.choice(years_pool)
            y_end = random.choice([y for y in years_pool if y >= y_start])
            params.append(("date_from", f"{y_start}-01-01"))
            params.append(("date_to", f"{y_end}-12-31"))

        # 1. Fetch Dashboard Summary
        resp_sum = local_snapshot_client.get("/api/v1/dashboard/summary", params=params)
        assert resp_sum.status_code == 200, f"Summary failed on params {params}"
        sum_total = resp_sum.json()["total_complaints"]

        # 2. Fetch By-Category
        resp_cat = local_snapshot_client.get("/api/v1/analytics/by-category", params=params)
        assert resp_cat.status_code == 200, f"Category failed on params {params}"
        cat_total = sum(item["total"] for item in resp_cat.json()["items"])

        # 3. Fetch Trends
        trend_params = list(params) + [("grain", "year")]
        resp_trend = local_snapshot_client.get("/api/v1/analytics/trends", params=trend_params)
        assert resp_trend.status_code == 200, f"Trends failed on params {params}"
        trend_total = sum(p["total"] for p in resp_trend.json()["total_series"]["points"])

        # 4. Fetch Breakdown
        brk_params = list(params) + [("dimension", "submitted_via"), ("limit", "5")]
        resp_brk = local_snapshot_client.get("/api/v1/analytics/breakdown", params=brk_params)
        assert resp_brk.status_code == 200, f"Breakdown failed on params {params}"
        brk_total = sum(item["total"] for item in resp_brk.json()["items"])

        # 5. Fetch Complaints Explorer
        resp_comp = local_snapshot_client.get("/api/v1/complaints", params=params)
        assert resp_comp.status_code == 200, f"Complaints failed on params {params}"
        comp_total = resp_comp.json()["total"]

        # Cross-check mutual equality (AC-4.3)
        assert sum_total == cat_total, (
            f"Mismatch summary ({sum_total}) vs category ({cat_total}) on {params}"
        )
        assert sum_total == trend_total, (
            f"Mismatch summary ({sum_total}) vs trends ({trend_total}) on {params}"
        )
        assert sum_total == brk_total, (
            f"Mismatch summary ({sum_total}) vs breakdown ({brk_total}) on {params}"
        )
        assert sum_total == comp_total, (
            f"Mismatch summary ({sum_total}) vs complaints ({comp_total}) on {params}"
        )


def test_data_quality_summary_matches_gold_report(local_snapshot_client: TestClient) -> None:
    """AC-4.4: Quality summary values equal the DQ report CSV; in_progress_share_pct computed (≈ 47.79%)."""
    resp = local_snapshot_client.get("/api/v1/quality/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_records"] == 62516
    assert data["overall_quality_score"] == 98.7
    assert data["status"] == "HIGH QUALITY"

    # Dimensions
    dim_map = {d["id"]: d["value"] for d in data["dimensions"]}
    assert dim_map["completeness"] == 99.6
    assert dim_map["validity"] == 98.8
    assert dim_map["uniqueness"] == 100.0
    assert dim_map["consistency"] == 100.0
    assert dim_map["ml_normality"] == 95.0

    # Anomalies block
    anom = data["anomalies"]
    assert anom["flagged"] == 3126
    assert anom["rate_pct"] == 5.0
    # Exactly 1,494 of 3,126 = 47.79%
    assert anom["in_progress_share_pct"] == pytest.approx(47.79, abs=0.01)

    # Model metadata
    assert data["model"]["type"] == "IsolationForest"
    assert data["model"]["contamination"] == 0.05
    assert data["model"]["n_estimators"] == 200


def test_complaints_export_reconciliation_on_local_snapshot(
    local_snapshot_client: TestClient,
) -> None:
    """Export on full local snapshot caps at EXPORT_MAX_ROWS (10,000) and marks X-Export-Truncated."""
    resp = local_snapshot_client.get("/api/v1/complaints/export")
    assert resp.status_code == 200
    assert resp.headers["X-Export-Truncated"] == "true"
    assert resp.headers["X-Export-Row-Count"] == "10000"
