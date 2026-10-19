"""
backend/app/schemas/analytics.py
--------------------------------
Pydantic response models for Meta, Dashboard, and Analytics endpoints (§13.2 and §13.3).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import DateCoverage, FiltersApplied, TimelyStats


# 1. Meta Endpoints Schemas
class CategoryMetaItem(BaseModel):
    """Category name and associated sub-categories."""

    model_config = ConfigDict(extra="ignore")

    name: str
    sub_categories: list[str]


class FiltersMetaResponse(BaseModel):
    """Metadata response detailing available filter dimensions and valid values (§13.2 #4)."""

    model_config = ConfigDict(extra="ignore")

    categories: list[CategoryMetaItem]
    submitted_via: list[str]
    state: list[str]
    company_response: list[str]
    timely: list[str]
    issues: list[str]
    coverage: DateCoverage


class DatasetMetaResponse(BaseModel):
    """Dataset provenance, record counts, and status indicators (§13.2 #3)."""

    model_config = ConfigDict(extra="ignore")

    data_origin: str
    data_status: str
    total_silver_records: int
    row_counts: dict[str, int]
    coverage: DateCoverage
    pipeline_refreshed_at: str
    quality_analysis_at: str | None
    skew_warning: bool
    schema_version: str = "1.0.0"
    warnings: list[str]


# 2. Dashboard / KPI Summary Schema
class DashboardSummaryResponse(BaseModel):
    """KPI and high-level analytical summary response (§13.2 #5)."""

    model_config = ConfigDict(extra="ignore")

    filters_applied: FiltersApplied
    total_complaints: int
    timely: TimelyStats
    in_progress_count: int
    category_count: int
    sub_category_count: int
    coverage: DateCoverage
    pipeline_refreshed_at: str
    data_origin: str


# 3. Category Analytics Schema
class CategoryItemSchema(BaseModel):
    """Category or sub-category analytical item."""

    model_config = ConfigDict(extra="ignore")

    category: str
    sub_category: str | None = None
    total: int
    share_pct: float | None
    timely_yes: int
    timely_no: int
    timely_unknown: int
    timely_rate: float | None
    timely_rate_all_cases: float | None


class ByCategoryResponse(BaseModel):
    """Volume and timely metrics by category or sub-category (§13.2 #6)."""

    model_config = ConfigDict(extra="ignore")

    group_by: Literal["category", "sub_category"]
    total: int
    items: list[CategoryItemSchema]
    filters_applied: FiltersApplied


# 4. Trends Schema
class TrendPointSchema(BaseModel):
    """A period's volume, partial status, and YoY growth."""

    model_config = ConfigDict(extra="ignore")

    period: str
    total: int
    is_partial: bool
    yoy_change_pct: float | None


class TrendSeriesSchema(BaseModel):
    """A named series of trend points."""

    model_config = ConfigDict(extra="ignore")

    key: str
    points: list[TrendPointSchema]


class TrendsResponse(BaseModel):
    """Time-series complaint trends with partial-period flags and YoY (§13.2 #7)."""

    model_config = ConfigDict(extra="ignore")

    grain: Literal["year", "month"]
    group_by: Literal["none", "category"]
    series: list[TrendSeriesSchema]
    total_series: TrendSeriesSchema
    filters_applied: FiltersApplied


# 5. Breakdown Schema
class BreakdownItemSchema(BaseModel):
    """One slice of a top-N breakdown."""

    model_config = ConfigDict(extra="ignore")

    name: str
    total: int
    share_pct: float | None
    timely_rate: float | None
    timely_rate_all_cases: float | None


class BreakdownResponse(BaseModel):
    """Top-N distribution breakdown with an 'Other' bucket (§13.2 #8)."""

    model_config = ConfigDict(extra="ignore")

    dimension: Literal["submitted_via", "state", "company_response", "issue", "product"]
    limit: int
    total: int
    items: list[BreakdownItemSchema]
    filters_applied: FiltersApplied
