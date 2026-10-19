"""
backend/tests/unit/test_loader.py
---------------------------------
Unit tests for data contracts, schema validation, and CSV loader logic (§942).
"""

import pandas as pd
import pytest

from app.core.errors import DataValidationError
from app.data.loader import (
    load_product_reference,
    load_silver_complaints,
    parse_csv_bytes,
)


@pytest.fixture
def valid_ref_csv() -> bytes:
    return b"""Product,Category,Sub_Category
Checking or savings account,Banking,Deposit Accounts
Credit card or prepaid card,Payments,Card Products
"""


@pytest.fixture
def valid_silver_csv() -> bytes:
    return b"""Complaint_ID,Submitted_Via,Date_submitted,Date_received,State,Product,Sub_Product,Issue,Sub_Issue,Company_Public_Response,Company_Response,Timely_Response
1001,Web,2022-01-15,2022-01-16,CA,Checking or savings account,Checking,Fee problem,Overdraft,None,Closed with explanation,Yes
1002,Phone,2022-02-10,2022-02-10,NY,Credit card or prepaid card,General,Billing dispute,None,None,In progress,None
"""


def test_parse_csv_bytes_with_bom():
    """BOM (utf-8-sig) must be stripped cleanly without corrupting the first column name."""
    csv_with_bom = (
        "\ufeffProduct,Category,Sub_Category\nMortgage,Lending,Real Estate Lending\n".encode(
            "utf-8"
        )
    )
    df = parse_csv_bytes(csv_with_bom)
    assert "Product" in df.columns
    assert len(df) == 1


def test_parse_csv_bytes_null_tokens():
    """All null-token variants normalise to None."""
    csv = b"""Product,Category,Sub_Category
Checking,nan,None
Card,null,N/A
Mortgage,NULL,
"""
    df = parse_csv_bytes(csv)
    assert df.loc[0, "Category"] is None
    assert df.loc[0, "Sub_Category"] is None
    assert df.loc[1, "Category"] is None
    assert df.loc[1, "Sub_Category"] is None
    assert df.loc[2, "Category"] is None
    assert df.loc[2, "Sub_Category"] is None


def test_empty_content_raises_validation_error():
    """Empty CSV bytes raise DataValidationError."""
    with pytest.raises(DataValidationError, match="CSV content is empty"):
        parse_csv_bytes(b"")


def test_missing_column_raises_validation_error(valid_ref_csv):
    """Missing required column raises DataValidationError with details."""
    ref_df = load_product_reference(valid_ref_csv)
    bad_csv = b"""Complaint_ID,Submitted_Via,State\n1,Web,CA\n"""
    with pytest.raises(DataValidationError, match="missing required columns"):
        load_silver_complaints(bad_csv, ref_df)


def test_duplicate_complaint_ids_deduplicated_with_warning(valid_ref_csv):
    """Duplicate IDs are deduplicated (keep first) and produce a warning in provenance."""
    ref_df = load_product_reference(valid_ref_csv)
    dupe_csv = b"""Complaint_ID,Submitted_Via,Date_submitted,Date_received,State,Product,Sub_Product,Issue,Sub_Issue,Company_Public_Response,Company_Response,Timely_Response
1001,Web,2022-01-15,2022-01-16,CA,Checking or savings account,Checking,Fee,None,None,Closed with explanation,Yes
1001,Phone,2022-01-15,2022-01-16,NY,Checking or savings account,Checking,Fee,None,None,Closed with explanation,No
"""
    df, warnings = load_silver_complaints(dupe_csv, ref_df)
    assert len(df) == 1
    assert df.iloc[0]["Submitted_Via"] == "Web"
    assert any("removed 1 duplicate Complaint_ID" in w for w in warnings)


def test_unmatched_product_maps_to_unmapped_with_warning(valid_ref_csv):
    """Unmatched product gets mapped to 'Unmapped' and records a warning."""
    ref_df = load_product_reference(valid_ref_csv)
    unmatched_csv = b"""Complaint_ID,Submitted_Via,Date_submitted,Date_received,State,Product,Sub_Product,Issue,Sub_Issue,Company_Public_Response,Company_Response,Timely_Response
1005,Web,2022-01-15,2022-01-16,CA,Nonexistent Mystery Product,None,Fee,None,None,Closed with explanation,Yes
"""
    df, warnings = load_silver_complaints(unmatched_csv, ref_df)
    assert len(df) == 1
    assert df.iloc[0]["Category"] == "Unmapped"
    assert df.iloc[0]["Sub_Category"] == "Unmapped"
    assert any("unmatched Products" in w for w in warnings)


def test_excessive_unparseable_dates_raises_error(valid_ref_csv):
    """Unparseable dates exceeding 1% threshold raise DataValidationError."""
    ref_df = load_product_reference(valid_ref_csv)
    bad_dates_csv = b"""Complaint_ID,Submitted_Via,Date_submitted,Date_received,State,Product,Sub_Product,Issue,Sub_Issue,Company_Public_Response,Company_Response,Timely_Response
1001,Web,invalid-date,2022-01-16,CA,Checking or savings account,None,Fee,None,None,Closed with explanation,Yes
"""
    with pytest.raises(DataValidationError, match="unparseable dates"):
        load_silver_complaints(bad_dates_csv, ref_df)


def test_routing_lag_and_timely_normalization(valid_ref_csv, valid_silver_csv):
    """Lag is computed as Date_received - Date_submitted; timely is normalized."""
    ref_df = load_product_reference(valid_ref_csv)
    df, warnings = load_silver_complaints(valid_silver_csv, ref_df)

    assert len(df) == 2
    # Row 1001: 2022-01-16 - 2022-01-15 = 1 day lag
    assert df.loc[df["Complaint_ID"] == "1001", "days_submitted_to_received"].iloc[0] == 1
    assert df.loc[df["Complaint_ID"] == "1001", "Timely_Response"].iloc[0] == "Yes"

    # Row 1002: same day = 0 lag, timeliness = NaN / None
    assert df.loc[df["Complaint_ID"] == "1002", "days_submitted_to_received"].iloc[0] == 0
    assert pd.isna(df.loc[df["Complaint_ID"] == "1002", "Timely_Response"].iloc[0])
