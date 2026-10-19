"""
backend/app/data/loader.py
--------------------------
Robust CSV parser and schema validator for Medallion data objects (§940).
Normalizes null tokens, enforces column contracts, handles BOMs, and computes derived fields.
"""

import io
import logging

import pandas as pd

from app.core.errors import DataValidationError
from app.data.contracts import (
    ALLOWED_NULL_TOKENS,
    PRODUCT_REFERENCE_CONTRACT,
    SILVER_COMPLAINTS_CONTRACT,
    DatasetContract,
)

logger = logging.getLogger(__name__)


def parse_csv_bytes(content: bytes) -> pd.DataFrame:
    """Parses raw CSV bytes into a trimmed string DataFrame, handling BOMs and null tokens."""
    if not content or len(content.strip()) == 0:
        raise DataValidationError("CSV content is empty")

    try:
        # utf-8-sig handles both UTF-8 with BOM and standard UTF-8
        df = pd.read_csv(
            io.BytesIO(content),
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )
    except Exception as exc:
        raise DataValidationError(f"Failed to parse CSV bytes: {exc}") from exc

    # Trim whitespace on string columns and normalize allowed null tokens
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(ALLOWED_NULL_TOKENS), col] = None

    return df


def validate_contract(df: pd.DataFrame, contract: DatasetContract) -> None:
    """Validates that all required columns are present and the table is not empty."""
    if len(df) == 0 and not contract.is_optional:
        raise DataValidationError(f"Dataset '{contract.name}' contains zero rows")

    missing = [c for c in contract.required_columns if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"Dataset '{contract.name}' is missing required columns: {missing}",
            details={"missing_columns": missing, "available_columns": list(df.columns)},
        )


def load_product_reference(content: bytes) -> pd.DataFrame:
    """Loads and validates the product-category reference table."""
    df = parse_csv_bytes(content)
    validate_contract(df, PRODUCT_REFERENCE_CONTRACT)
    return df[PRODUCT_REFERENCE_CONTRACT.required_columns].copy()


def load_silver_complaints(
    content: bytes,
    ref_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Parses, validates, types, and enriches Silver complaint records.
    Returns the enriched DataFrame and a list of provenance warnings.
    """
    df = parse_csv_bytes(content)
    validate_contract(df, SILVER_COMPLAINTS_CONTRACT)
    warnings: list[str] = []

    # 1. Deduplication by Complaint_ID
    initial_count = len(df)
    df = df.drop_duplicates(subset=["Complaint_ID"], keep="first").copy()
    dropped_dupes = initial_count - len(df)
    if dropped_dupes > 0:
        msg = f"Deduplication: removed {dropped_dupes} duplicate Complaint_ID rows"
        warnings.append(msg)
        logger.warning(msg)

    # 2. Date parsing and validation
    for date_col in ["Date_submitted", "Date_received"]:
        parsed_dates = pd.to_datetime(df[date_col], format="%Y-%m-%d", errors="coerce")
        unparseable = int(parsed_dates.isna().sum())
        if unparseable > 0:
            unparseable_pct = (unparseable / len(df)) * 100
            if unparseable_pct > 1.0:
                raise DataValidationError(
                    f"Column '{date_col}' has {unparseable_pct:.2f}% unparseable dates (threshold is 1.0%)",
                    details={"column": date_col, "unparseable_count": unparseable},
                )
            warnings.append(f"Column '{date_col}' has {unparseable} unparseable dates")
        df[f"{date_col}_dt"] = parsed_dates

    # 3. CFPB Routing lag calculation (Date_received - Date_submitted)
    lag = (df["Date_received_dt"] - df["Date_submitted_dt"]).dt.days
    negative_lag_count = int((lag < 0).sum())
    if negative_lag_count > 0:
        msg = f"Routing lag anomaly: {negative_lag_count} rows have Date_received < Date_submitted"
        warnings.append(msg)
        logger.warning(msg)

    df["days_submitted_to_received"] = lag

    # 4. Normalize Timely_Response to "Yes", "No", or None
    timely_lower = df["Timely_Response"].str.lower()
    df["Timely_Response"] = timely_lower.map({"yes": "Yes", "no": "No"})

    # 5. Join to Product Reference lookup
    if not {"Product", "Category", "Sub_Category"}.issubset(ref_df.columns):
        raise DataValidationError("Product reference table missing required columns for join")

    # Drop existing Category/Sub_Category if already present in silver to avoid collision
    cols_to_drop = [c for c in ["Category", "Sub_Category"] if c in df.columns]
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)

    df = df.merge(ref_df[["Product", "Category", "Sub_Category"]], on="Product", how="left")
    unmatched_count = int(df["Category"].isna().sum())
    if unmatched_count > 0:
        msg = f"Join warning: {unmatched_count} rows had unmatched Products; labelled as 'Unmapped'"
        warnings.append(msg)
        logger.warning(msg)
        df["Category"] = df["Category"].fillna("Unmapped")
        df["Sub_Category"] = df["Sub_Category"].fillna("Unmapped")

    # 6. Extract integer year for fast trend partitioning
    df["Year"] = df["Date_submitted_dt"].dt.year

    return df, warnings


def load_gold_table(content: bytes, contract: DatasetContract) -> pd.DataFrame:
    """Loads and validates a Gold aggregate table according to its contract."""
    df = parse_csv_bytes(content)
    validate_contract(df, contract)
    return df
