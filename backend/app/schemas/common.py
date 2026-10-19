"""
backend/app/schemas/common.py
-----------------------------
Common schema models and sub-structures shared across API endpoints (§13.1).
"""

from pydantic import BaseModel, ConfigDict, Field


class FiltersApplied(BaseModel):
    """Normalized filter parameters recorded in API response payloads."""

    model_config = ConfigDict(extra="ignore")

    category: list[str] = Field(default_factory=list)
    sub_category: list[str] = Field(default_factory=list)
    submitted_via: list[str] = Field(default_factory=list)
    state: list[str] = Field(default_factory=list)
    company_response: list[str] = Field(default_factory=list)
    timely: list[str] = Field(default_factory=list)
    issue: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None


class DateCoverage(BaseModel):
    """Date span covered by complaints in scope."""

    model_config = ConfigDict(extra="ignore")

    start: str
    end: str


class TimelyStats(BaseModel):
    """Timeliness breakdown and dual rate calculations."""

    model_config = ConfigDict(extra="ignore")

    yes: int
    no: int
    unknown: int
    rate: float | None = Field(
        ...,
        description="Primary timely response rate (Yes / (Yes + No) * 100). None if denominator is 0.",
    )
    rate_denominator: int = Field(
        ...,
        description="Cases with recorded timeliness (Yes + No), excluding open cases.",
    )
    rate_all_cases: float | None = Field(
        ...,
        description="Legacy timely response rate dividing by total complaints (Yes / Total * 100).",
    )
