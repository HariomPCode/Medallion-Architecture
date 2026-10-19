"""
backend/app/api/meta.py
-----------------------
Dataset provenance and available filter dimensions metadata endpoints (§13.2 #3 and #4).
"""

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_snapshot
from app.data.snapshot import Snapshot, get_snapshot_manager
from app.schemas.analytics import CategoryMetaItem, DatasetMetaResponse, FiltersMetaResponse
from app.schemas.common import DateCoverage

router = APIRouter(prefix="/api/v1/meta", tags=["Metadata"])


@router.get(
    "/dataset", response_model=DatasetMetaResponse, summary="Dataset provenance and health metadata"
)
async def get_dataset_metadata(
    request: Request,
    response: Response,
    snapshot: Snapshot = Depends(get_current_snapshot),
) -> DatasetMetaResponse:
    """Returns dataset provenance, status, row counts, and refresh timestamps."""
    response.headers["Cache-Control"] = "private, max-age=60"

    manager = getattr(request.app.state, "snapshot_manager", None) or get_snapshot_manager()
    df = snapshot.silver_complaints

    start_date = str(df["Date_submitted"].min()) if not df.empty else "1970-01-01"
    end_date = str(df["Date_submitted"].max()) if not df.empty else "1970-01-01"

    # Determine quality analysis timestamp if available from run metadata
    quality_analysis_at: str | None = None
    if snapshot.gold_dq_run is not None and not snapshot.gold_dq_run.empty:
        if "generated_at_utc" in snapshot.gold_dq_run.columns:
            quality_analysis_at = str(snapshot.gold_dq_run["generated_at_utc"].iloc[0])

    return DatasetMetaResponse(
        data_origin=snapshot.provenance.get("data_origin", "unknown"),
        data_status=manager.status,
        total_silver_records=len(df),
        row_counts=snapshot.provenance.get("row_counts", {}),
        coverage=DateCoverage(start=start_date, end=end_date),
        pipeline_refreshed_at=snapshot.loaded_at,
        quality_analysis_at=quality_analysis_at,
        skew_warning=snapshot.skew_warning,
        schema_version="1.0.0",
        warnings=snapshot.provenance.get("warnings", []),
    )


@router.get(
    "/filters", response_model=FiltersMetaResponse, summary="Available filter dimensions and values"
)
async def get_filters_metadata(
    response: Response,
    snapshot: Snapshot = Depends(get_current_snapshot),
) -> FiltersMetaResponse:
    """Returns available dimensions, valid values, and hierarchy mappings for filtering."""
    response.headers["Cache-Control"] = "private, max-age=60"

    df = snapshot.silver_complaints

    # 1. Categories and sub-categories mapping
    cat_items: list[CategoryMetaItem] = []
    if not df.empty:
        cat_groups = df.groupby("Category", observed=True)["Sub_Category"].unique()
        for cat_name, sub_cats in cat_groups.items():
            valid_subs = sorted([str(s) for s in sub_cats if s is not None and str(s) != "nan"])
            cat_items.append(CategoryMetaItem(name=str(cat_name), sub_categories=valid_subs))
        cat_items.sort(key=lambda x: x.name)

    # 2. Other distinct dimensions
    channels = sorted(df["Submitted_Via"].dropna().unique().tolist()) if not df.empty else []
    states = sorted(df["State"].dropna().unique().tolist()) if not df.empty else []
    responses = sorted(df["Company_Response"].dropna().unique().tolist()) if not df.empty else []
    issues = sorted(df["Issue"].dropna().unique().tolist()) if not df.empty else []

    start_date = str(df["Date_submitted"].min()) if not df.empty else "1970-01-01"
    end_date = str(df["Date_submitted"].max()) if not df.empty else "1970-01-01"

    return FiltersMetaResponse(
        categories=cat_items,
        submitted_via=channels,
        state=states,
        company_response=responses,
        timely=["yes", "no", "unknown"],
        issues=issues,
        coverage=DateCoverage(start=start_date, end=end_date),
    )
