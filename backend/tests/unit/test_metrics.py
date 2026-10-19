"""
backend/tests/unit/test_metrics.py
----------------------------------
Unit tests for central Metric Registry and docs/METRICS.md synchronization (§1026).
"""

import os

from app.domain.metrics import METRIC_REGISTRY, generate_metrics_markdown, get_metric


def test_metric_registry_contains_all_required_metrics() -> None:
    expected_ids = [f"M-{i:02d}" for i in range(1, 16)]
    for m_id in expected_ids:
        assert m_id in METRIC_REGISTRY, f"Missing metric {m_id} in registry"
        metric = get_metric(m_id)
        assert metric.id == m_id
        assert metric.label
        assert metric.formula_text
        assert metric.source_columns
        assert metric.null_handling
        assert metric.limitations


def test_routing_delay_is_never_labeled_company_response_time() -> None:
    m09 = get_metric("M-09")
    assert "routing" in m09.label.lower() or "routing" in m09.formula_text.lower()
    assert "company response time" not in m09.label.lower()
    assert "CFPB routing delay" in m09.limitations


def test_dual_timely_rates_have_distinct_denominators() -> None:
    m03 = get_metric("M-03")
    m04 = get_metric("M-04")
    assert m03.denominator != m04.denominator
    assert "timely_yes + timely_no" in str(m03.denominator)
    assert "total_complaints" in str(m04.denominator)


def test_metrics_markdown_is_not_stale() -> None:
    """Verifies that docs/METRICS.md is byte-for-byte identical to the generated output."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    metrics_doc_path = os.path.join(repo_root, "docs", "METRICS.md")
    assert os.path.exists(metrics_doc_path), "docs/METRICS.md does not exist"

    with open(metrics_doc_path, "r", encoding="utf-8") as f:
        existing_content = f.read()

    generated_content = generate_metrics_markdown()
    # Normalize line endings
    assert existing_content.replace("\r\n", "\n") == generated_content.replace("\r\n", "\n"), (
        "docs/METRICS.md is out of sync with backend/app/domain/metrics.py. "
        "Run generator to refresh documentation."
    )
