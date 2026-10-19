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
