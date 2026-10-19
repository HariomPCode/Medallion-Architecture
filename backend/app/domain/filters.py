"""
backend/app/domain/filters.py
-----------------------------
Shared filter specification and validation engine for all analytics endpoints (§13.1 and §1027).
Enforces strict parameter parsing, snapshot dimension validation, and fast vectorised filtering.
"""

from datetime import date
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.errors import ValidationException


class ComplaintFilters(BaseModel):
    """Normalized query filters for analytics, dashboard, and explorer endpoints."""

    model_config = ConfigDict(extra="forbid")

    category: list[str] = Field(default_factory=list)
    sub_category: list[str] = Field(default_factory=list)
    submitted_via: list[str] = Field(default_factory=list)
    state: list[str] = Field(default_factory=list)
    company_response: list[str] = Field(default_factory=list)
    timely: list[Literal["yes", "no", "unknown"]] = Field(default_factory=list)
    issue: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None

    @field_validator(
        "category",
        "sub_category",
        "submitted_via",
        "state",
        "company_response",
        "issue",
        "timely",
        mode="after",
    )
    @classmethod
    def validate_max_items(cls, v: list[Any], info: Any) -> list[Any]:
        if len(v) > 20:
            field_name = info.field_name
            raise ValueError(
                f"Filter '{field_name}' exceeds maximum allowed items (20). Received {len(v)}."
            )
        return v

    @field_validator("date_from", "date_to", mode="after")
    @classmethod
    def validate_date_format(cls, v: str | None, info: Any) -> str | None:
        if v is None:
            return None
        try:
            # Validate standard YYYY-MM-DD
            parts = v.split("-")
            if len(parts) != 3 or len(parts[0]) != 4:
                raise ValueError()
            date.fromisoformat(v)
        except Exception:
            field_name = info.field_name
            raise ValueError(
                f"Field '{field_name}' must be formatted as YYYY-MM-DD. Received '{v}'."
            )
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "ComplaintFilters":
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError(
                    f"date_from ('{self.date_from}') must be less than or equal to date_to ('{self.date_to}')."
                )
        return self

    def validate_against_snapshot(self, snapshot: Any) -> None:
        """
        Validates filter values against the distinct values present in the loaded snapshot.
        Raises ValidationException (HTTP 422) with allowed_values list if unknown values are detected.
        """
        df: pd.DataFrame = snapshot.silver_complaints

        check_map: list[tuple[str, list[str], str]] = [
            ("category", self.category, "Category"),
            ("sub_category", self.sub_category, "Sub_Category"),
            ("submitted_via", self.submitted_via, "Submitted_Via"),
            ("state", self.state, "State"),
            ("company_response", self.company_response, "Company_Response"),
            ("issue", self.issue, "Issue"),
        ]

        for filter_name, filter_vals, col_name in check_map:
            if not filter_vals:
                continue
            allowed = set(df[col_name].dropna().unique())
            invalid = [val for val in filter_vals if val not in allowed]
            if invalid:
                sorted_allowed = sorted(list(allowed))
                raise ValidationException(
                    message=f"Unknown value(s) for filter '{filter_name}': {invalid}",
                    details={
                        "field": filter_name,
                        "invalid_values": invalid,
                        "allowed_values": sorted_allowed[:50],
                    },
                )

    def to_applied_dict(self) -> dict[str, Any]:
        """Returns a sanitized dict of applied filters for API response envelopes."""
        return {
            "category": self.category,
            "sub_category": self.sub_category,
            "submitted_via": self.submitted_via,
            "state": self.state,
            "company_response": self.company_response,
            "timely": self.timely,
            "issue": self.issue,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }


def apply_filters(df: pd.DataFrame, filters: ComplaintFilters) -> pd.DataFrame:
    """
    Applies vectorised boolean masks to filter complaints in memory.
    Returns a filtered slice of the DataFrame.
    """
    if df.empty:
        return df

    mask = pd.Series(True, index=df.index)

    if filters.category:
        mask &= df["Category"].isin(filters.category)

    if filters.sub_category:
        mask &= df["Sub_Category"].isin(filters.sub_category)

    if filters.submitted_via:
        mask &= df["Submitted_Via"].isin(filters.submitted_via)

    if filters.state:
        mask &= df["State"].isin(filters.state)

    if filters.company_response:
        mask &= df["Company_Response"].isin(filters.company_response)

    if filters.issue:
        mask &= df["Issue"].isin(filters.issue)

    if filters.timely:
        timely_mask = pd.Series(False, index=df.index)
        for t in filters.timely:
            if t == "yes":
                timely_mask |= df["Timely_Response"] == "Yes"
            elif t == "no":
                timely_mask |= df["Timely_Response"] == "No"
            elif t == "unknown":
                timely_mask |= df["Timely_Response"].isna()
        mask &= timely_mask

    if filters.date_from:
        mask &= df["Date_submitted"] >= filters.date_from

    if filters.date_to:
        mask &= df["Date_submitted"] <= filters.date_to

    return df[mask]
