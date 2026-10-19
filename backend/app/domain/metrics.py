"""
backend/app/domain/metrics.py
-----------------------------
Central Metric Registry for Finance Complaints Medallion platform (§6 and §1026).
Defines authoritative specifications for metrics M-01 through M-15.
No other code or component may re-implement or redefine these formulas.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MetricDefinition:
    """Authoritative metadata and calculation specification for an analytical metric."""

    id: str
    api_name: str
    label: str
    formula_text: str
    source_columns: list[str]
    denominator: Optional[str]
    null_handling: str
    limitations: str


METRIC_REGISTRY: dict[str, MetricDefinition] = {
    "M-01": MetricDefinition(
        id="M-01",
        api_name="total_complaints",
        label="Total Complaints",
        formula_text="COUNT(DISTINCT Complaint_ID)",
        source_columns=["Complaint_ID"],
        denominator=None,
        null_handling="Complaint_ID is unique and non-null by data contract.",
        limitations="Dataset is a 62,516-row extract; not the full CFPB historical database.",
    ),
    "M-02": MetricDefinition(
        id="M-02",
        api_name="category_share_pct",
        label="Category Volume Share (%)",
        formula_text="(category_total / filtered_total) * 100",
        source_columns=["Category", "Complaint_ID"],
        denominator="filtered_total (Total complaints matching active filters)",
        null_handling="Unmapped products assigned to 'Unmapped' category if encountered. Returns None if denominator is 0.",
        limitations="Shares are relative to the active filtered subset of this extract.",
    ),
    "M-03": MetricDefinition(
        id="M-03",
        api_name="timely_response_rate",
        label="Timely Response Rate (Primary)",
        formula_text="(timely_yes / (timely_yes + timely_no)) * 100",
        source_columns=["Timely_Response"],
        denominator="timely_yes + timely_no (Resolved cases with recorded timeliness)",
        null_handling="Excludes open/in-progress cases with null timeliness. Returns None if denominator is 0.",
        limitations="Excludes 1,494 unresolved cases. Recent months contain higher proportions of pending cases.",
    ),
    "M-04": MetricDefinition(
        id="M-04",
        api_name="timely_response_rate_all_cases",
        label="Timely Response Rate — All Cases (Legacy)",
        formula_text="(timely_yes / total_complaints) * 100",
        source_columns=["Timely_Response", "Complaint_ID"],
        denominator="total_complaints (All cases in scope, including open/unresolved cases)",
        null_handling="Open/unresolved cases count in denominator as not timely. Returns None if total_complaints is 0.",
        limitations="Reproduces README/Appendix B legacy figure (93.77%). Understates compliance by penalizing active cases.",
    ),
    "M-05": MetricDefinition(
        id="M-05",
        api_name="timely_counts",
        label="Timely Response Counts (Yes / No / Unknown)",
        formula_text="SUM(Timely_Response == 'Yes'), SUM(Timely_Response == 'No'), SUM(Timely_Response IS NULL)",
        source_columns=["Timely_Response"],
        denominator=None,
        null_handling="Explicitly tallies 'Unknown' / pending responses alongside Yes and No.",
        limitations="timely_unknown exactly equals In progress count in this dataset (1,494 records).",
    ),
    "M-06": MetricDefinition(
        id="M-06",
        api_name="in_progress_count",
        label="In Progress Cases",
        formula_text="SUM(Company_Response == 'In progress')",
        source_columns=["Company_Response"],
        denominator=None,
        null_handling="Company_Response is non-null.",
        limitations="Represents cases actively under review by financial institutions at time of extract (May-Aug 2023).",
    ),
    "M-07": MetricDefinition(
        id="M-07",
        api_name="complaints_by_period",
        label="Complaints by Period (Year / Month)",
        formula_text="COUNT(Complaint_ID) GROUP BY Period(Date_submitted)",
        source_columns=["Date_submitted", "Complaint_ID"],
        denominator=None,
        null_handling="Missing calendar periods in the range are zero-filled. Periods tagged with is_partial flag.",
        limitations="2017 (starts May 1) and 2023 (ends Aug 28) are incomplete calendar years.",
    ),
    "M-08": MetricDefinition(
        id="M-08",
        api_name="yoy_change_pct",
        label="Year-over-Year Growth (%)",
        formula_text="((N_current_year - N_prior_year) / N_prior_year) * 100",
        source_columns=["Date_submitted", "Complaint_ID"],
        denominator="N_prior_year (Complaints in preceding calendar year)",
        null_handling="Evaluates to None if either current or prior year is partial, or if N_prior_year == 0.",
        limitations="Valid only between complete calendar years (2018 through 2022). Null for 2017, 2018, and 2023.",
    ),
    "M-09": MetricDefinition(
        id="M-09",
        api_name="days_submitted_to_received",
        label="Routing Delay (CFPB to Company)",
        formula_text="(Date_received - Date_submitted) in days",
        source_columns=["Date_submitted", "Date_received"],
        denominator=None,
        null_handling="Null if either date is missing. Negative values flagged.",
        limitations="Measures CFPB intake and CFPB routing delay, NOT company response or resolution duration.",
    ),
    "M-10": MetricDefinition(
        id="M-10",
        api_name="anomaly_metrics",
        label="Anomaly Score & Flags (Isolation Forest)",
        formula_text="IsolationForest(n_estimators=200, contamination=0.05, random_state=42)",
        source_columns=["complaints_anomaly_gold.csv: anomaly_score, is_anomaly"],
        denominator="total_scored_records",
        null_handling="Pre-computed in Gold layer; joined to Silver by Complaint_ID.",
        limitations="contamination=0.05 fixes the flagged proportion to approx 5.0% by construction.",
    ),
    "M-11": MetricDefinition(
        id="M-11",
        api_name="overall_quality_score",
        label="Overall Data Quality Score",
        formula_text="0.25*Completeness + 0.20*Validity + 0.20*Consistency + 0.15*Uniqueness + 0.20*ML_Normality",
        source_columns=["data_quality_report_gold.csv"],
        denominator=None,
        null_handling="Pre-computed in Medallion pipeline. Evaluates to 98.7% (HIGH QUALITY).",
        limitations="Composite score from notebook. ML Normality is fixed by contamination parameter.",
    ),
    "M-12": MetricDefinition(
        id="M-12",
        api_name="quality_dimensions",
        label="Data Quality Dimensions",
        formula_text="Five dimensions: Completeness (99.6%), Validity (98.8%), Uniqueness (100.0%), Consistency (100.0%), ML Normality (95.0%)",
        source_columns=["data_quality_report_gold.csv"],
        denominator=None,
        null_handling="Captured directly from pipeline report object.",
        limitations="Completeness/Validity are slightly reduced due to valid open cases with null timeliness.",
    ),
    "M-13": MetricDefinition(
        id="M-13",
        api_name="data_coverage",
        label="Dataset Date Coverage",
        formula_text="MIN(Date_submitted) to MAX(Date_submitted)",
        source_columns=["Date_submitted"],
        denominator=None,
        null_handling="Computed from non-null Date_submitted values.",
        limitations="Represents business 'as-of' date range (2017-05-01 to 2023-08-28).",
    ),
    "M-14": MetricDefinition(
        id="M-14",
        api_name="pipeline_refreshed_at",
        label="Pipeline Refresh Timestamp",
        formula_text="Blob/file last_modified timestamp of Silver complaints object",
        source_columns=["Provenance metadata"],
        denominator=None,
        null_handling="Fallback to system snapshot load time if blob mtime unavailable.",
        limitations="Represents pipeline write timestamp, distinct from data coverage and quality analysis dates.",
    ),
    "M-15": MetricDefinition(
        id="M-15",
        api_name="quality_analysis_at",
        label="Quality Analysis Timestamp",
        formula_text="generated_at_utc from run metadata or DQ report blob last_modified",
        source_columns=["Provenance metadata", "data_quality_run_gold.csv"],
        denominator=None,
        null_handling="Fallback to pipeline_refreshed_at if run metadata absent.",
        limitations="Represents when data quality validation models were trained and scored.",
    ),
}


def get_metric(metric_id: str) -> MetricDefinition:
    """Look up a metric definition by ID (e.g. 'M-01')."""
    if metric_id not in METRIC_REGISTRY:
        raise KeyError(f"Metric '{metric_id}' not found in registry.")
    return METRIC_REGISTRY[metric_id]


def generate_metrics_markdown() -> str:
    """Generates the authoritative Markdown document for docs/METRICS.md from the registry."""
    lines = [
        "# Analytical Metrics Registry",
        "",
        "**Document:** `docs/METRICS.md`  ",
        "**Phase:** Phase 3 — Core Analytics APIs  ",
        "**Source of Truth:** `backend/app/domain/metrics.py`  ",
        "",
        "> [!IMPORTANT]",
        "> This document is automatically generated from the central Metric Registry in `backend/app/domain/metrics.py`.",
        "> All REST endpoints, AI assistant tools, and dashboard visualisations must adhere to these definitions.",
        "",
        "---",
        "",
        "## Metric Definitions (M-01 through M-15)",
        "",
        "| ID | API Name | Label | Formula | Denominator | Null Handling | Limitations |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for m_id, m in sorted(METRIC_REGISTRY.items()):
        denom_str = m.denominator if m.denominator else "—"
        # Escape pipe characters for markdown table
        formula_clean = m.formula_text.replace("|", "\\|")
        lines.append(
            f"| **{m.id}** | `{m.api_name}` | {m.label} | `{formula_clean}` | {denom_str} | {m.null_handling} | {m.limitations} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## Key Analytical Distinctions",
            "",
            "### 1. Dual Timely-Response Measures (D-06)",
            "- **Primary Rate (`M-03`):** Evaluates `timely_yes / (timely_yes + timely_no) * 100`. In our baseline: `58,619 / 61,022 = 96.06%`.",
            "  - *Rationale:* Open cases (`In progress`) have not reached a resolution date and cannot be determined untimely prior to expiration.",
            "- **Legacy Rate (`M-04`):** Evaluates `timely_yes / total_complaints * 100`. In our baseline: `58,619 / 62,516 = 93.77%`.",
            "  - *Rationale:* Preserved strictly to reconcile with historical README tables and Gold outputs.",
            "",
            "### 2. CFPB Routing Lag vs Company Response Time (M-09)",
            "- `Date_received - Date_submitted` represents the duration CFPB took to process and forward the complaint to the financial company.",
            "- It must **never** be labeled as 'Company Response Time' in any API, documentation, or user interface.",
            "",
            "### 3. Partial Calendar Years (M-07 & M-08)",
            "- **2017:** Incomplete coverage begins May 1, 2017.",
            "- **2023:** Incomplete coverage ends August 28, 2023.",
            "- Year-over-Year calculations (`M-08`) are strictly permitted only between complete calendar years (2018 $\\to$ 2019, 2019 $\\to$ 2020, 2020 $\\to$ 2021, 2021 $\\to$ 2022). All other years must return `null`.",
            "",
        ]
    )

    return "\n".join(lines)
