"""
backend/app/api/analytics.py
----------------------------
Core analytics endpoints: by-category, trends, breakdown, and KPIs (§13.2 #6–8).
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_current_snapshot, get_filters_dependency
from app.data.snapshot import Snapshot
from app.domain.aggregates import (
    compute_breakdown,
    compute_by_category,
    compute_totals,
    compute_trends,
)
from app.domain.filters import ComplaintFilters, apply_filters
from app.schemas.analytics import (
    BreakdownItemSchema,
    BreakdownResponse,
    ByCategoryResponse,
    CategoryItemSchema,
    DashboardSummaryResponse,
    TrendPointSchema,
    TrendSeriesSchema,
    TrendsResponse,
)
from app.schemas.common import DateCoverage, FiltersApplied, TimelyStats

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


# 1. By-Category Analytics (Endpoints: /analytics/by-category and /analytics/categories)
@router.get(
    "/by-category",
    response_model=ByCategoryResponse,
    summary="Category and sub-category volume and timely response rates",
)
@router.get(
    "/categories",
    response_model=ByCategoryResponse,
    summary="Category and sub-category volume and timely response rates (alias)",
)
async def get_by_category(
    response: Response,
    group_by: Literal["category", "sub_category"] = Query(
        default="category", description="Aggregation level: category or sub_category"
    ),
    sort: Literal["total", "timely_rate", "name"] = Query(
        default="total", description="Sort field: total, timely_rate, or name"
    ),
    order: Literal["asc", "desc"] = Query(
        default="desc", description="Sort direction: asc or desc"
    ),
    snapshot: Snapshot = Depends(get_current_snapshot),
    filters: ComplaintFilters = Depends(
        get_filters_dependency(allowed_extra_params={"group_by", "sort", "order"})
    ),
) -> ByCategoryResponse:
    """Returns volume, share, and timeliness breakdown for categories or sub-categories."""
    response.headers["Cache-Control"] = "private, max-age=60"

    filtered_df = apply_filters(snapshot.silver_complaints, filters)
    total_filtered = len(filtered_df)

    items = compute_by_category(
        df=filtered_df,
        total_filtered=total_filtered,
        group_by=group_by,
        sort=sort,
        order=order,
    )

    schema_items = [
        CategoryItemSchema(
            category=it.category,
            sub_category=it.sub_category,
            total=it.total,
            share_pct=it.share_pct,
            timely_yes=it.timely_yes,
            timely_no=it.timely_no,
            timely_unknown=it.timely_unknown,
            timely_rate=it.timely_rate,
            timely_rate_all_cases=it.timely_rate_all_cases,
        )
        for it in items
    ]

    return ByCategoryResponse(
        group_by=group_by,
        total=total_filtered,
        items=schema_items,
        filters_applied=FiltersApplied(**filters.to_applied_dict()),
    )


# 2. Trends Analytics
@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Time-series complaint trends with partial-period flags and YoY growth",
)
async def get_trends(
    response: Response,
    grain: Literal["year", "month"] = Query(
        default="year", description="Time granularity: year or month"
    ),
    group_by: Literal["none", "category"] = Query(
        default="none", description="Series breakdown: none or category"
    ),
    snapshot: Snapshot = Depends(get_current_snapshot),
    filters: ComplaintFilters = Depends(
        get_filters_dependency(allowed_extra_params={"grain", "group_by"})
    ),
) -> TrendsResponse:
    """Returns time-series volume trends, data-driven partial period flags, and YoY growth."""
    response.headers["Cache-Control"] = "private, max-age=60"

    filtered_df = apply_filters(snapshot.silver_complaints, filters)

    # Determine global snapshot coverage for data-driven partial checks
    cov_start = (
        str(snapshot.silver_complaints["Date_submitted"].min())
        if not snapshot.silver_complaints.empty
        else "1970-01-01"
    )
    cov_end = (
        str(snapshot.silver_complaints["Date_submitted"].max())
        if not snapshot.silver_complaints.empty
        else "1970-01-01"
    )

    series_list, total_series = compute_trends(
        df=filtered_df,
        coverage_start=cov_start,
        coverage_end=cov_end,
        grain=grain,
        group_by=group_by,
    )

    def to_schema_series(s: Any) -> TrendSeriesSchema:
        return TrendSeriesSchema(
            key=s.key,
            points=[
                TrendPointSchema(
                    period=p.period,
                    total=p.total,
                    is_partial=p.is_partial,
                    yoy_change_pct=p.yoy_change_pct,
                )
                for p in s.points
            ],
        )

    return TrendsResponse(
        grain=grain,
        group_by=group_by,
        series=[to_schema_series(s) for s in series_list],
        total_series=to_schema_series(total_series),
        filters_applied=FiltersApplied(**filters.to_applied_dict()),
    )


# 3. Breakdown Analytics
@router.get(
    "/breakdown",
    response_model=BreakdownResponse,
    summary="Top-N distribution breakdown by dimension",
)
async def get_breakdown(
    response: Response,
    dimension: Literal["submitted_via", "state", "company_response", "issue", "product"] = Query(
        ..., description="Target dimension to group and rank"
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Max top items (1-50)"),
    snapshot: Snapshot = Depends(get_current_snapshot),
    filters: ComplaintFilters = Depends(
        get_filters_dependency(allowed_extra_params={"dimension", "limit"})
    ),
) -> BreakdownResponse:
    """Returns top-N categories along the selected dimension with an 'Other' remainder bucket."""
    response.headers["Cache-Control"] = "private, max-age=60"

    filtered_df = apply_filters(snapshot.silver_complaints, filters)
    total_filtered = len(filtered_df)

    items = compute_breakdown(
        df=filtered_df,
        total_filtered=total_filtered,
        dimension=dimension,
        limit=limit,
    )

    schema_items = [
        BreakdownItemSchema(
            name=it.name,
            total=it.total,
            share_pct=it.share_pct,
            timely_rate=it.timely_rate,
            timely_rate_all_cases=it.timely_rate_all_cases,
        )
        for it in items
    ]

    return BreakdownResponse(
        dimension=dimension,
        limit=limit,
        total=total_filtered,
        items=schema_items,
        filters_applied=FiltersApplied(**filters.to_applied_dict()),
    )


# 4. KPI Summary (Endpoint: /analytics/kpis)
@router.get(
    "/kpis",
    response_model=DashboardSummaryResponse,
    summary="High-level KPI metrics summary",
)
async def get_kpis(
    response: Response,
    snapshot: Snapshot = Depends(get_current_snapshot),
    filters: ComplaintFilters = Depends(get_filters_dependency()),
) -> DashboardSummaryResponse:
    """Calculates KPI summary indicators (total, timely rates, in-progress, coverage)."""
    response.headers["Cache-Control"] = "private, max-age=60"

    filtered_df = apply_filters(snapshot.silver_complaints, filters)
    totals = compute_totals(filtered_df)

    if not filtered_df.empty:
        start_date = str(filtered_df["Date_submitted"].min())
        end_date = str(filtered_df["Date_submitted"].max())
        cat_count = int(filtered_df["Category"].nunique())
        sub_cat_count = int(filtered_df["Sub_Category"].nunique())
    else:
        start_date = (
            str(snapshot.silver_complaints["Date_submitted"].min())
            if not snapshot.silver_complaints.empty
            else "1970-01-01"
        )
        end_date = (
            str(snapshot.silver_complaints["Date_submitted"].max())
            if not snapshot.silver_complaints.empty
            else "1970-01-01"
        )
        cat_count = 0
        sub_cat_count = 0

    return DashboardSummaryResponse(
        filters_applied=FiltersApplied(**filters.to_applied_dict()),
        total_complaints=totals.total,
        timely=TimelyStats(
            yes=totals.timely_yes,
            no=totals.timely_no,
            unknown=totals.timely_unknown,
            rate=totals.timely_rate,
            rate_denominator=totals.rate_denominator,
            rate_all_cases=totals.timely_rate_all_cases,
        ),
        in_progress_count=totals.in_progress_count,
        category_count=cat_count,
        sub_category_count=sub_cat_count,
        coverage=DateCoverage(start=start_date, end=end_date),
        pipeline_refreshed_at=snapshot.loaded_at,
        data_origin=snapshot.provenance.get("data_origin", "unknown"),
    )
