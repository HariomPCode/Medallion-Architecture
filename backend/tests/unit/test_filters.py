"""
backend/tests/unit/test_filters.py
----------------------------------
Unit tests for ComplaintFilters validation, snapshot dimension checking, and masking (§1027).
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from pydantic import ValidationError

from app.core.errors import ValidationException
from app.domain.filters import ComplaintFilters, apply_filters


def test_filters_default_initialization() -> None:
    f = ComplaintFilters()
    assert f.category == []
    assert f.sub_category == []
    assert f.date_from is None
    assert f.date_to is None
    assert f.timely == []


def test_filters_rejects_extra_parameters() -> None:
    with pytest.raises(ValidationError):
        ComplaintFilters(unknown_param="invalid")  # type: ignore[call-arg]


def test_filters_rejects_invalid_date_format() -> None:
    with pytest.raises(ValidationError):
        ComplaintFilters(date_from="2023/01/01")

    with pytest.raises(ValidationError):
        ComplaintFilters(date_to="not-a-date")


def test_filters_rejects_inverted_date_range() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ComplaintFilters(date_from="2023-08-01", date_to="2023-01-01")
    assert "date_from" in str(exc_info.value)


def test_filters_rejects_more_than_20_items() -> None:
    many_categories = [f"Cat_{i}" for i in range(21)]
    with pytest.raises(ValidationError) as exc_info:
        ComplaintFilters(category=many_categories)
    assert "exceeds maximum allowed items (20)" in str(exc_info.value)


def test_validate_against_snapshot_valid() -> None:
    mock_df = pd.DataFrame(
        {
            "Category": ["Banking", "Payments"],
            "Sub_Category": ["Deposit Accounts", "Card Products"],
            "Submitted_Via": ["Web", "Phone"],
            "State": ["CA", "NY"],
            "Company_Response": ["Closed with explanation", "In progress"],
            "Issue": ["Managing an account", "Fraud"],
        }
    )
    mock_snap = MagicMock()
    mock_snap.silver_complaints = mock_df

    f = ComplaintFilters(
        category=["Banking"],
        state=["CA", "NY"],
        submitted_via=["Web"],
    )
    # Should pass without raising
    f.validate_against_snapshot(mock_snap)


def test_validate_against_snapshot_unknown_value() -> None:
    mock_df = pd.DataFrame(
        {
            "Category": ["Banking", "Payments"],
            "Sub_Category": ["Deposit Accounts", "Card Products"],
            "Submitted_Via": ["Web", "Phone"],
            "State": ["CA", "NY"],
            "Company_Response": ["Closed with explanation", "In progress"],
            "Issue": ["Managing an account", "Fraud"],
        }
    )
    mock_snap = MagicMock()
    mock_snap.silver_complaints = mock_df

    f = ComplaintFilters(category=["UnknownCategory"])
    with pytest.raises(ValidationException) as exc_info:
        f.validate_against_snapshot(mock_snap)
    assert "Unknown value(s) for filter 'category'" in exc_info.value.message
    assert "allowed_values" in exc_info.value.details


def test_apply_filters_multi_dimension() -> None:
    df = pd.DataFrame(
        {
            "Complaint_ID": [1, 2, 3, 4],
            "Category": ["Banking", "Banking", "Payments", "Lending"],
            "Sub_Category": ["Deposit", "Deposit", "Card", "Mortgage"],
            "Submitted_Via": ["Web", "Phone", "Web", "Referral"],
            "State": ["CA", "NY", "CA", "TX"],
            "Company_Response": [
                "Closed with explanation",
                "In progress",
                "Closed with explanation",
                "Closed with explanation",
            ],
            "Timely_Response": ["Yes", None, "No", "Yes"],
            "Date_submitted": ["2021-05-01", "2021-06-01", "2022-01-10", "2022-05-15"],
            "Issue": ["Issue A", "Issue B", "Issue A", "Issue C"],
        }
    )

    # 1. Filter by category
    f1 = ComplaintFilters(category=["Banking"])
    res1 = apply_filters(df, f1)
    assert len(res1) == 2
    assert list(res1["Complaint_ID"]) == [1, 2]

    # 2. Filter by timely enum: "unknown" (null in Timely_Response)
    f2 = ComplaintFilters(timely=["unknown"])
    res2 = apply_filters(df, f2)
    assert len(res2) == 1
    assert res2.iloc[0]["Complaint_ID"] == 2

    # 3. Filter by date range
    f3 = ComplaintFilters(date_from="2022-01-01", date_to="2022-12-31")
    res3 = apply_filters(df, f3)
    assert len(res3) == 2
    assert list(res3["Complaint_ID"]) == [3, 4]

    # 4. Filter by multiple conditions
    f4 = ComplaintFilters(category=["Banking", "Payments"], state=["CA"], timely=["yes", "no"])
    res4 = apply_filters(df, f4)
    assert len(res4) == 2
    assert list(res4["Complaint_ID"]) == [1, 3]
