"""
backend/app/data/contracts.py
-----------------------------
Data schemas, column requirements, and constraint definitions for Medallion pipeline objects (§5.3, §5.4, §939).
"""

from typing import NamedTuple

# Standard set of string representations treated as null/empty per A-11
ALLOWED_NULL_TOKENS = frozenset(
    {
        "",
        "nan",
        "NaN",
        "NAN",
        "None",
        "none",
        "null",
        "NULL",
        "NA",
        "N/A",
        "n/a",
    }
)


class DatasetContract(NamedTuple):
    name: str
    required_columns: list[str]
    is_optional: bool = False


# Contracts for Silver and Reference objects
SILVER_COMPLAINTS_CONTRACT = DatasetContract(
    name="silver_complaints",
    required_columns=[
        "Complaint_ID",
        "Submitted_Via",
        "Date_submitted",
        "Date_received",
        "State",
        "Product",
        "Sub_Product",
        "Issue",
        "Sub_Issue",
        "Company_Public_Response",
        "Company_Response",
        "Timely_Response",
    ],
)

PRODUCT_REFERENCE_CONTRACT = DatasetContract(
    name="product_category_reference",
    required_columns=["Product", "Category", "Sub_Category"],
)

# Contracts for Gold pipeline objects
GOLD_CATEGORY_CONTRACT = DatasetContract(
    name="gold_category",
    required_columns=["Category", "Sub_Category", "total_complaints", "timely_response_pct"],
)

GOLD_TREND_CONTRACT = DatasetContract(
    name="gold_trend",
    required_columns=["Year", "Category", "total_complaints"],
)

GOLD_ANOMALY_CONTRACT = DatasetContract(
    name="gold_anomaly",
    required_columns=[
        "Complaint_ID",
        "Category",
        "Sub_Category",
        "Company_Response",
        "Days_to_Respond",
        "anomaly_score",
        "is_anomaly",
    ],
)

GOLD_DQ_REPORT_CONTRACT = DatasetContract(
    name="gold_dq_report",
    required_columns=[
        "total_records",
        "completeness_pct",
        "validity_pct",
        "uniqueness_pct",
        "consistency_pct",
        "ml_normality_pct",
        "overall_quality_score",
        "status",
        "mlflow_run_id",
    ],
)

GOLD_DQ_RUN_CONTRACT = DatasetContract(
    name="gold_dq_run",
    required_columns=[
        "generated_at_utc",
        "silver_row_count",
        "model_type",
        "n_estimators",
        "contamination",
        "random_state",
        "feature_cols",
        "mlflow_run_id",
    ],
    is_optional=True,
)
