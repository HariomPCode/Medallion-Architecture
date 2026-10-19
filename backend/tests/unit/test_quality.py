"""
backend/tests/unit/test_quality.py
----------------------------------
Unit tests for Data Quality Center domain operations (§13.2 #12, #13).
Tests decomposed dimension weighting, data-driven notes, anomaly aggregations,
run-metadata presence vs absence, and deterministic observations.
"""

import pandas as pd
import pytest

from app.core.config import Settings
from app.core.errors import DataSourceError, ValidationException
from app.data.snapshot import Snapshot, SnapshotManager
from app.domain.quality import get_quality_anomalies, get_quality_summary


@pytest.fixture
def tiny_snapshot():
    settings = Settings(DATA_MODE="fixture")
    manager = SnapshotManager(settings)
    import asyncio

    return asyncio.run(manager.build_snapshot())


def test_get_quality_summary_dimensions_and_limitations(tiny_snapshot):
    """Quality summary must decompose 5 dimensions with exact weights and provide audit caveats."""
    summary = get_quality_summary(tiny_snapshot)

    assert summary.total_records > 0
    assert summary.overall_quality_score > 0.0
    assert summary.status in ("HIGH QUALITY", "MODERATE QUALITY", "LOW QUALITY")

    # Dimensions check
    dim_ids = [d.id for d in summary.dimensions]
    assert dim_ids == ["completeness", "validity", "consistency", "uniqueness", "ml_normality"]

    weights = {d.id: d.weight for d in summary.dimensions}
    assert weights["completeness"] == 0.25
    assert weights["validity"] == 0.20
    assert weights["consistency"] == 0.20
    assert weights["uniqueness"] == 0.15
    assert weights["ml_normality"] == 0.20
    assert sum(weights.values()) == pytest.approx(1.0)

    # Data-driven notes check
    comp_dim = next(d for d in summary.dimensions if d.id == "completeness")
    assert "open ('In progress') cases" in comp_dim.note

    # Mandatory limitations check (§6 A-05..A-08)
    assert len(summary.limitations) >= 4
    assert any("ML Normality is derived" in lim for lim in summary.limitations)
    assert any("open ('In progress') complaints" in lim for lim in summary.limitations)

    # In tiny fixture, gold_dq_run is absent -> source is notebook_constant
    assert summary.model.available is False
    assert summary.model.source == "notebook_constant"


def test_get_quality_summary_with_run_metadata(tiny_snapshot):
    """When run metadata DataFrame is present, model.available is True with source 'run_metadata'."""
    # Synthesize a mock gold_dq_run DataFrame
    mock_run_df = pd.DataFrame(
        [
            {
                "generated_at_utc": "2026-10-19T12:00:00Z",
                "silver_row_count": len(tiny_snapshot.silver_complaints),
                "model_type": "IsolationForest",
                "n_estimators": 200,
                "contamination": 0.05,
                "random_state": 42,
                "feature_cols": "Days_to_Respond,is_timely,Category_code",
                "mlflow_run_id": "test_mlflow_run_123",
            }
        ]
    )

    enriched_snapshot = Snapshot(
        silver_complaints=tiny_snapshot.silver_complaints,
        product_reference=tiny_snapshot.product_reference,
        gold_category=tiny_snapshot.gold_category,
        gold_trend=tiny_snapshot.gold_trend,
        gold_anomaly=tiny_snapshot.gold_anomaly,
        gold_dq_report=tiny_snapshot.gold_dq_report,
        gold_dq_run=mock_run_df,
        provenance=tiny_snapshot.provenance,
        loaded_at=tiny_snapshot.loaded_at,
        skew_warning=tiny_snapshot.skew_warning,
    )

    summary = get_quality_summary(enriched_snapshot)
    assert summary.model.available is True
    assert summary.model.source == "run_metadata"
    assert summary.model.mlflow_run_id == "test_mlflow_run_123"
    assert summary.timestamps.quality_analysis_at == "2026-10-19T12:00:00Z"


def test_get_quality_summary_missing_report_raises_error(tiny_snapshot):
    """Missing gold_dq_report table raises DataSourceError (HTTP 503)."""
    empty_report_snapshot = Snapshot(
        silver_complaints=tiny_snapshot.silver_complaints,
        product_reference=tiny_snapshot.product_reference,
        gold_category=tiny_snapshot.gold_category,
        gold_trend=tiny_snapshot.gold_trend,
        gold_anomaly=tiny_snapshot.gold_anomaly,
        gold_dq_report=pd.DataFrame(),
        gold_dq_run=None,
        provenance=tiny_snapshot.provenance,
        loaded_at=tiny_snapshot.loaded_at,
        skew_warning=tiny_snapshot.skew_warning,
    )

    with pytest.raises(DataSourceError):
        get_quality_summary(empty_report_snapshot)


def test_get_quality_anomalies_filtering_and_annotations(tiny_snapshot):
    """Anomalies endpoint returns paginated records with deterministic observation flags."""
    # List all flagged
    res = get_quality_anomalies(tiny_snapshot, only_flagged=True, page=1, page_size=10)
    assert res.total >= 0
    assert len(res.items) <= 10

    if res.items:
        first = res.items[0]
        assert isinstance(first.annotations.open_case, bool)
        assert isinstance(first.annotations.long_routing_delay, bool)
        assert isinstance(first.annotations.timely_no, bool)
        assert first.annotations_note == "Observations, not model explanations"

    # Invalid sort column
    with pytest.raises(ValidationException) as exc:
        get_quality_anomalies(tiny_snapshot, sort_by="invalid_col")
    assert "Invalid anomaly sort column" in str(exc.value)
