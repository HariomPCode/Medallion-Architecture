"""
backend/app/api/dashboard.py
----------------------------
Dashboard summary and KPI block endpoint (§13.2 #5 and §13.3).
"""

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_current_snapshot, get_filters_dependency
from app.data.snapshot import Snapshot
from app.domain.aggregates import compute_totals
from app.domain.filters import ComplaintFilters, apply_filters
from app.schemas.analytics import DashboardSummaryResponse
from app.schemas.common import DateCoverage, FiltersApplied, TimelyStats

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="High-level KPI and timeliness metrics summary",
)
async def get_dashboard_summary(
    response: Response,
    snapshot: Snapshot = Depends(get_current_snapshot),
    filters: ComplaintFilters = Depends(get_filters_dependency()),
) -> DashboardSummaryResponse:
    """Returns total volume, dual timely response rates, in-progress counts, and coverage."""
    response.headers["Cache-Control"] = "private, max-age=60"

    filtered_df = apply_filters(snapshot.silver_complaints, filters)
    totals = compute_totals(filtered_df)

    if not filtered_df.empty:
        start_date = str(filtered_df["Date_submitted"].min())
        end_date = str(filtered_df["Date_submitted"].max())
        cat_count = int(filtered_df["Category"].nunique())
        sub_cat_count = int(filtered_df["Sub_Category"].nunique())
    else:
        # If filtered set is empty, coverage displays snapshot baseline range
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
