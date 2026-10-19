"""
backend/tests/assistant/test_tools.py
-------------------------------------
Unit tests and Tool/REST parity tests for tools T1–T8 (§1206, §1255).
Proves that every tool result matches the corresponding REST endpoint payload under identical inputs.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.assistant.tools import ToolArgumentError, execute_tool
from app.data.snapshot import get_snapshot_manager
from app.main import app


@pytest.fixture(scope="module")
def snapshot():
    manager = get_snapshot_manager()
    if manager.current_snapshot is None:
        import asyncio

        asyncio.run(manager.startup_load())
    return manager.current_snapshot


@pytest.fixture(scope="module")
def client(snapshot) -> Any:
    with TestClient(app) as test_client:
        yield test_client


def test_t1_dataset_overview_and_rest_parity(client: TestClient, snapshot) -> None:
    """T1 get_dataset_overview must match /api/v1/dashboard/summary exactly."""
    tool_env = execute_tool("get_dataset_overview", {}, snapshot)
    assert tool_env["tool"] == "get_dataset_overview"
    assert tool_env["provenance"]["metric_ids"] == [
        "M-01",
        "M-02",
        "M-03",
        "M-04",
        "M-05",
        "M-06",
        "M-13",
        "M-14",
    ]

    rest_res = client.get("/api/v1/dashboard/summary")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["total_complaints"] == rest_data["total_complaints"]
    assert t_res["timely"]["rate"] == rest_data["timely"]["rate"]
    assert t_res["timely"]["rate_denominator"] == rest_data["timely"]["rate_denominator"]
    assert t_res["timely"]["rate_all_cases"] == rest_data["timely"]["rate_all_cases"]
    assert t_res["in_progress_count"] == rest_data["in_progress_count"]
    assert t_res["category_count"] == rest_data["category_count"]
    assert t_res["sub_category_count"] == rest_data["sub_category_count"]


def test_t2_compare_categories_and_rest_parity(client: TestClient, snapshot) -> None:
    """T2 compare_categories must match /api/v1/analytics/by-category."""
    tool_env = execute_tool(
        "compare_categories", {"group_by": "category", "sort": "total"}, snapshot
    )
    assert tool_env["tool"] == "compare_categories"
    assert "M-01" in tool_env["provenance"]["metric_ids"]

    rest_res = client.get("/api/v1/analytics/by-category?group_by=category&sort=total")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["total"] == rest_data["total"]
    assert len(t_res["items"]) == len(rest_data["items"])

    for t_item, r_item in zip(t_res["items"], rest_data["items"]):
        assert t_item["category"] == r_item["category"]
        assert t_item["total"] == r_item["total"]
        assert t_item["share_pct"] == r_item["share_pct"]
        assert t_item["timely_rate"] == r_item["timely_rate"]


def test_t3_get_trend_and_rest_parity(client: TestClient, snapshot) -> None:
    """T3 get_trend must match /api/v1/analytics/trends."""
    tool_env = execute_tool("get_trend", {"grain": "year", "group_by": "none"}, snapshot)
    assert tool_env["tool"] == "get_trend"

    rest_res = client.get("/api/v1/analytics/trends?grain=year&group_by=none")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    t_points = t_res["total_series"]["points"]
    r_points = rest_data["total_series"]["points"]
    assert len(t_points) == len(r_points)

    for tp, rp in zip(t_points, r_points):
        assert tp["period"] == rp["period"]
        assert tp["total"] == rp["total"]
        assert tp["is_partial"] == rp["is_partial"]
        assert tp["yoy_change_pct"] == rp["yoy_change_pct"]


def test_t4_get_breakdown_and_rest_parity(client: TestClient, snapshot) -> None:
    """T4 get_breakdown must match /api/v1/analytics/breakdown."""
    tool_env = execute_tool("get_breakdown", {"dimension": "submitted_via", "limit": 5}, snapshot)
    assert tool_env["tool"] == "get_breakdown"

    rest_res = client.get("/api/v1/analytics/breakdown?dimension=submitted_via&limit=5")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["total"] == rest_data["total"]
    assert len(t_res["items"]) == len(rest_data["items"])

    for ti, ri in zip(t_res["items"], rest_data["items"]):
        assert ti["name"] == ri["name"]
        assert ti["total"] == ri["total"]
        assert ti["share_pct"] == ri["share_pct"]


def test_t5_search_complaints_and_rest_parity(client: TestClient, snapshot) -> None:
    """T5 search_complaints must match /api/v1/complaints whitelisted output."""
    tool_env = execute_tool("search_complaints", {"limit": 5}, snapshot)
    assert tool_env["tool"] == "search_complaints"

    rest_res = client.get("/api/v1/complaints?page_size=5")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["total"] == rest_data["total"]
    assert len(t_res["items"]) == 5

    for ti, ri in zip(t_res["items"], rest_data["items"]):
        assert ti["complaint_id"] == ri["complaint_id"]
        assert ti["category"] == ri["category"]
        assert ti["date_submitted"] == ri["date_submitted"]


def test_t6_get_quality_summary_and_rest_parity(client: TestClient, snapshot) -> None:
    """T6 get_quality_summary must match /api/v1/quality/summary."""
    tool_env = execute_tool("get_quality_summary", {}, snapshot)
    assert tool_env["tool"] == "get_quality_summary"

    rest_res = client.get("/api/v1/quality/summary")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["overall_quality_score"] == rest_data["overall_quality_score"]
    assert t_res["status"] == rest_data["status"]
    assert t_res["anomalies"]["flagged"] == rest_data["anomalies"]["flagged"]
    assert len(t_res["dimensions"]) == len(rest_data["dimensions"])


def test_t7_list_anomalies_and_rest_parity(client: TestClient, snapshot) -> None:
    """T7 list_anomalies must match /api/v1/quality/anomalies."""
    tool_env = execute_tool("list_anomalies", {"limit": 5, "sort": "score"}, snapshot)
    assert tool_env["tool"] == "list_anomalies"

    rest_res = client.get("/api/v1/quality/anomalies?page_size=5&sort=score")
    assert rest_res.status_code == 200
    rest_data = rest_res.json()

    t_res = tool_env["result"]
    assert t_res["total"] == rest_data["total"]
    assert len(t_res["items"]) == len(rest_data["items"])

    for ti, ri in zip(t_res["items"], rest_data["items"]):
        assert ti["complaint_id"] == ri["complaint_id"]
        assert ti["anomaly_score"] == ri["anomaly_score"]


def test_t8_explain_metric(snapshot) -> None:
    """T8 explain_metric returns registry definition for M-03 and M-04."""
    tool_env_m03 = execute_tool("explain_metric", {"metric_id": "M-03"}, snapshot)
    res_m03 = tool_env_m03["result"]
    assert res_m03["metric_id"] == "M-03"
    assert "timely" in res_m03["api_name"].lower()
    assert res_m03["denominator"] != ""

    tool_env_m04 = execute_tool("explain_metric", {"name": "timely_rate_all_cases"}, snapshot)
    res_m04 = tool_env_m04["result"]
    assert res_m04["metric_id"] == "M-04"


def test_tools_reject_invalid_arguments(snapshot) -> None:
    """Tools must raise ToolArgumentError (HTTP 422) on malformed arguments."""
    with pytest.raises(ToolArgumentError):
        execute_tool("compare_categories", {"group_by": "invalid_group"}, snapshot)

    with pytest.raises(ToolArgumentError):
        execute_tool("get_breakdown", {"dimension": "fake_dim"}, snapshot)

    with pytest.raises(ToolArgumentError):
        execute_tool("unknown_tool_name", {}, snapshot)


def test_tools_are_pure_and_read_only(snapshot) -> None:
    """Executing tools must never mutate underlying snapshot DataFrames."""
    initial_len = len(snapshot.silver_complaints)
    initial_cols = list(snapshot.silver_complaints.columns)

    execute_tool("get_dataset_overview", {}, snapshot)
    execute_tool("compare_categories", {"group_by": "category"}, snapshot)
    execute_tool("get_trend", {"grain": "year"}, snapshot)

    assert len(snapshot.silver_complaints) == initial_len
    assert list(snapshot.silver_complaints.columns) == initial_cols
