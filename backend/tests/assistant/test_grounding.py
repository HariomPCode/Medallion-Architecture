"""
backend/tests/assistant/test_grounding.py
-----------------------------------------
Authoritative tests for numeric grounding verification and deterministic fallback renderer (§1227, §1256).
Enforces the core requirement: must not present unsupported numerical claims as verified facts.
"""

import pytest

from app.assistant.grounding import (
    extract_numerals,
    generate_data_blocks,
    render_fallback,
    verify_grounding,
)
from app.data.snapshot import get_snapshot_manager


@pytest.fixture(scope="module")
def snapshot():
    manager = get_snapshot_manager()
    if manager.current_snapshot is None:
        import asyncio

        asyncio.run(manager.startup_load())
    return manager.current_snapshot


def test_extract_numerals() -> None:
    """Ensure extraction handles thousands separators, decimals, and percentages while ignoring dates."""
    text = (
        "In 2022, there were 62,516 complaints filed on 2022-05-15. "
        "The timely response rate was 96.06%, up by +26.39% from previous, with 1,494 open cases."
    )
    tokens = extract_numerals(text)
    assert "62,516" in tokens
    assert "96.06%" in tokens
    assert "+26.39%" in tokens
    assert "1,494" in tokens
    # ISO date 2022-05-15 must not be included as a raw number token
    assert "2022-05-15" not in tokens


def test_verify_grounding_accepts_valid_numbers_and_rounding() -> None:
    """Exact and appropriately rounded numbers matching tool results must be accepted."""
    tool_results = [
        {
            "tool": "get_dataset_overview",
            "result": {
                "total_complaints": 62516,
                "timely": {"rate": 96.06, "rate_denominator": 61022},
                "in_progress_count": 1494,
            },
        }
    ]

    valid_narrative = (
        "There were 62,516 complaints in total. The timely response rate was 96.1% "
        "(or 96.06%) across 61,022 rated cases, with 1,494 cases in progress."
    )
    res = verify_grounding(valid_narrative, tool_results)
    assert res.is_grounded is True
    assert len(res.ungrounded_numbers) == 0


def test_verify_grounding_rejects_fabricated_numbers() -> None:
    """Any unsupported numerical claim must be caught and rejected."""
    tool_results = [
        {
            "tool": "get_dataset_overview",
            "result": {
                "total_complaints": 62516,
                "timely": {"rate": 96.06, "rate_denominator": 61022},
            },
        }
    ]

    fabricated_narrative = (
        "There were 62,516 complaints, but 8,500 were invalid and the satisfaction score was 74.2%."
    )
    res = verify_grounding(fabricated_narrative, tool_results)
    assert res.is_grounded is False
    assert "8,500" in res.ungrounded_numbers or "74.2%" in res.ungrounded_numbers


def test_verify_grounding_allows_small_ordinals_and_years() -> None:
    """Small ranking ordinals and dataset coverage years are permitted linguistic tokens."""
    tool_results = [
        {
            "tool": "compare_categories",
            "result": {
                "total": 62516,
                "items": [{"category": "Banking", "total": 24814, "share_pct": 39.69}],
            },
        }
    ]

    narrative = "In 2021, Banking was the 1st category with 24,814 complaints representing 39.69% of the top 5."
    res = verify_grounding(narrative, tool_results)
    assert res.is_grounded is True


def test_verify_grounding_adversarial_rejection() -> None:
    """Adversarial response filled with fabricated numbers must be rejected."""
    tool_results = [
        {
            "tool": "get_dataset_overview",
            "result": {"total_complaints": 62516},
        }
    ]

    adversarial_text = " ".join([f"metric_{i} is {i * 111}" for i in range(15, 30)])
    res = verify_grounding(adversarial_text, tool_results)
    assert res.is_grounded is False
    assert len(res.ungrounded_numbers) > 10


def test_render_fallback_always_passes_grounding(snapshot) -> None:
    """The deterministic fallback renderer must produce output that 100% passes grounding validation."""
    tool_results = [
        {
            "tool": "get_dataset_overview",
            "result": {
                "total_complaints": 62516,
                "timely": {"rate": 96.06, "rate_denominator": 61022},
                "in_progress_count": 1494,
            },
        },
        {
            "tool": "compare_categories",
            "result": {
                "total": 62516,
                "items": [
                    {"category": "Banking", "total": 24814, "share_pct": 39.69, "timely_rate": 96.4}
                ],
            },
        },
    ]

    fallback_text = render_fallback(tool_results, snapshot)
    assert fallback_text != ""
    assert "62,516" in fallback_text
    assert "96.06%" in fallback_text
    assert "24,814" in fallback_text

    # Must pass grounding check with zero ungrounded tokens
    g_res = verify_grounding(fallback_text, tool_results, snapshot)
    assert g_res.is_grounded is True
    assert len(g_res.ungrounded_numbers) == 0


def test_generate_data_blocks(snapshot) -> None:
    """generate_data_blocks creates KPI, table, and series blocks directly from tool results."""
    tool_results = [
        {
            "tool": "get_dataset_overview",
            "result": {
                "total_complaints": 62516,
                "timely": {"rate": 96.06},
                "in_progress_count": 1494,
                "category_count": 5,
            },
        },
        {
            "tool": "compare_categories",
            "result": {
                "group_by": "category",
                "items": [
                    {"category": "Banking", "total": 24814, "share_pct": 39.69, "timely_rate": 96.4}
                ],
            },
        },
    ]

    blocks = generate_data_blocks(tool_results, snapshot)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "kpi"
    assert blocks[0]["rows"][0][0] == 62516
    assert blocks[1]["type"] == "table"
    assert blocks[1]["rows"][0][0] == "Banking"


def test_render_fallback_all_tools(snapshot) -> None:
    """Verify render_fallback handles all remaining tools and always passes grounding verification."""
    # Empty tool results
    empty_fallback = render_fallback([], snapshot)
    assert f"{len(snapshot.silver_complaints):,}" in empty_fallback
    assert verify_grounding(empty_fallback, [], snapshot).is_grounded is True

    # Tool results covering get_trend, compare_categories empty, get_breakdown, quality, anomalies, explain, search
    tool_results = [
        {
            "tool": "get_trend",
            "result": {
                "grain": "year",
                "total_series": {
                    "points": [
                        {
                            "period": "2017",
                            "total": 3521,
                            "is_partial": True,
                            "yoy_change_pct": None,
                        },
                        {
                            "period": "2021",
                            "total": 15820,
                            "is_partial": False,
                            "yoy_change_pct": 12.5,
                        },
                        {
                            "period": "2023",
                            "total": 7890,
                            "is_partial": True,
                            "yoy_change_pct": -5.2,
                        },
                    ]
                },
            },
        },
        {
            "tool": "compare_categories",
            "result": {"items": [], "total": 0, "group_by": "category"},
        },
        {
            "tool": "get_breakdown",
            "result": {
                "dimension": "submitted_via",
                "total": 62516,
                "items": [{"name": "Web", "total": 45000, "share_pct": 71.98}],
            },
        },
        {
            "tool": "get_quality_summary",
            "result": {
                "overall_quality_score": 98.5,
                "status": "HIGH QUALITY",
                "anomalies": {"flagged": 3125, "rate_pct": 5.0},
            },
        },
        {
            "tool": "list_anomalies",
            "result": {
                "total": 3125,
                "count": 5,
                "items": [{"complaint_id": 1}],
            },
        },
        {
            "tool": "explain_metric",
            "result": {
                "metric_id": "M-03",
                "label": "Timely Response Rate",
                "formula_text": "Timely / Resolved",
                "denominator": "Resolved Complaints",
                "baseline_values": {"baseline_denominator": 61022},
            },
        },
        {
            "tool": "explain_metric",
            "result": {
                "metric_id": "M-04",
                "label": "Timely Over Total Rate",
                "formula_text": "Timely / Total",
                "denominator": "Total Complaints",
                "baseline_values": {"baseline_denominator": 62516},
            },
        },
        {
            "tool": "explain_metric",
            "result": {
                "metric_id": "M-01",
                "label": "Total Complaints",
                "formula_text": "Count(id)",
                "denominator": "N/A",
                "baseline_values": {},
            },
        },
        {
            "tool": "search_complaints",
            "result": {
                "total": 120,
                "count": 10,
                "items": [{"complaint_id": 10}],
            },
        },
    ]

    fallback = render_fallback(tool_results, snapshot)
    assert "3,521" in fallback
    assert "15,820" in fallback
    assert "submitted_via" in fallback
    assert "45,000" in fallback
    assert "98.5" in fallback
    assert "3,125" in fallback
    assert "61,022" in fallback
    assert "M-04" in fallback
    assert "120" in fallback

    # Grounding check must pass for the complete fallback narrative
    g_res = verify_grounding(fallback, tool_results, snapshot)
    assert g_res.is_grounded is True


def test_render_fallback_empty_trend_and_breakdown(snapshot) -> None:
    """Empty trends or breakdown results should render informative fallbacks."""
    tool_results = [
        {"tool": "get_trend", "result": {"total_series": {"points": []}}},
        {"tool": "get_breakdown", "result": {"dimension": "channel", "items": []}},
    ]
    fb = render_fallback(tool_results, snapshot)
    assert "No trend time-series points matched" in fb
    assert "No breakdown data available for dimension channel" in fb


def test_generate_data_blocks_all_tools(snapshot) -> None:
    """Verify data blocks generation for get_trend, get_breakdown, and get_quality_summary."""
    tool_results = [
        {
            "tool": "get_trend",
            "result": {
                "grain": "year",
                "total_series": {
                    "points": [
                        {
                            "period": "2020",
                            "total": 10000,
                            "is_partial": False,
                            "yoy_change_pct": 5.0,
                        },
                        {
                            "period": "2021",
                            "total": 12000,
                            "is_partial": True,
                            "yoy_change_pct": None,
                        },
                    ]
                },
            },
        },
        {
            "tool": "get_breakdown",
            "result": {
                "dimension": "state",
                "items": [{"name": "CA", "total": 8000, "share_pct": 12.8}],
                "other": {"total": 54516, "share_pct": 87.2},
            },
        },
        {
            "tool": "get_quality_summary",
            "result": {
                "dimensions": [
                    {"label": "Completeness", "value": "100%", "weight": "0.35", "note": "Perfect"}
                ]
            },
        },
    ]

    blocks = generate_data_blocks(tool_results, snapshot)
    assert len(blocks) == 3

    # Trend series block
    assert blocks[0]["type"] == "series"
    assert blocks[0]["rows"][0][0] == "2020"
    assert blocks[0]["rows"][0][2] == "No"
    assert blocks[0]["rows"][0][3] == "5.0%"
    assert blocks[0]["rows"][1][2] == "Yes"
    assert blocks[0]["rows"][1][3] == "—"

    # Breakdown table block (with Other row)
    assert blocks[1]["type"] == "table"
    assert blocks[1]["rows"][0][0] == "CA"
    assert blocks[1]["rows"][1][0] == "Other"
    assert blocks[1]["rows"][1][1] == 54516

    # Quality summary table block
    assert blocks[2]["type"] == "table"
    assert blocks[2]["rows"][0][0] == "Completeness"


def test_grounding_edge_cases_and_constants() -> None:
    """Verify grounding handles empty text, mathematical constants, string numbers in tool results."""
    # Empty / whitespace narratives
    assert verify_grounding("", []).is_grounded is True
    assert verify_grounding("No numbers here at all.", []).is_grounded is True

    # Mathematical constants (0, 1, 100, 100%, 0%)
    math_narrative = "The error rate is 0%, completeness is 100%, and count was 1."
    res = verify_grounding(math_narrative, [])
    assert res.is_grounded is True

    # Tool results with boolean, nested dictionaries with digit keys, and text containing numerals
    complex_tool = [
        {
            "tool": "custom",
            "result": {
                "is_active": True,
                "years_map": {"2022": 4500},
                "notes": "There are 750 special cases reported.",
            },
            "arguments": {
                "extra_code": "code_999",
            },
        }
    ]
    res_valid = verify_grounding(
        "In 2022 there were 4500 cases and 750 special cases.", complex_tool
    )
    assert res_valid.is_grounded is True
