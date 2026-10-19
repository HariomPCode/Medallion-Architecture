"""
backend/app/api/complaints.py
-----------------------------
FastAPI router for Complaint Explorer endpoints (§13.2 #9, #10, #11).
Provides paginated browsing, single-complaint detail, and streaming CSV export.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_snapshot, get_filters_dependency
from app.core.config import get_settings
from app.core.errors import ValidationException
from app.data.snapshot import Snapshot
from app.domain.complaints import (
    get_complaint_detail,
    search_complaints,
    stream_complaints_csv,
)
from app.domain.filters import ComplaintFilters
from app.schemas.complaints import ComplaintDetailResponse, ComplaintListResponse

router = APIRouter(prefix="/api/v1/complaints", tags=["Complaints Explorer"])

ALLOWED_COMPLAINT_PARAMS = {
    "q",
    "sort",
    "sort_by",
    "order",
    "sort_dir",
    "page",
    "page_size",
}

ALLOWED_EXPORT_PARAMS = {
    "q",
    "sort",
    "sort_by",
    "order",
    "sort_dir",
}


@router.get("", response_model=ComplaintListResponse)
def list_complaints(
    request: Request,
    filters: ComplaintFilters = Depends(get_filters_dependency(ALLOWED_COMPLAINT_PARAMS)),
    snapshot: Snapshot = Depends(get_current_snapshot),
    q: str | None = Query(None, description="Exact Complaint_ID search (digits only, <= 12 chars)"),
    sort: str | None = Query(None, description="Sort column alias"),
    sort_by: str = Query("date_submitted", description="Sort column"),
    order: str | None = Query(None, description="Sort direction alias ('asc' or 'desc')"),
    sort_dir: str = Query("desc", description="Sort direction ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page (max 100)"),
) -> ComplaintListResponse:
    """
    Paginated, filtered, and deterministically sorted complaint browsing (§13.2 #9).
    Exposes only whitelisted public fields and joins anomaly status.
    """
    effective_sort = sort if sort is not None else sort_by
    effective_order = order if order is not None else sort_dir

    return search_complaints(
        snapshot=snapshot,
        filters=filters,
        q=q,
        sort_by=effective_sort,
        sort_dir=effective_order,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
def export_complaints(
    request: Request,
    filters: ComplaintFilters = Depends(get_filters_dependency(ALLOWED_EXPORT_PARAMS)),
    snapshot: Snapshot = Depends(get_current_snapshot),
    q: str | None = Query(None, description="Exact Complaint_ID filter"),
    sort: str | None = Query(None, description="Sort column alias"),
    sort_by: str = Query("date_submitted", description="Sort column"),
    order: str | None = Query(None, description="Sort direction alias"),
    sort_dir: str = Query("desc", description="Sort direction"),
) -> StreamingResponse:
    """
    Streaming CSV export of filtered complaints (§13.2 #11).
    Enforces EXPORT_MAX_ROWS capping, formula-injection guards, and export headers.
    """
    # TODO(AC-4.1): Connect RATE_LIMIT_EXPORT (10/hour) when slowapi limiter is wired in Phase 6.
    settings = get_settings()
    effective_sort = sort if sort is not None else sort_by
    effective_order = order if order is not None else sort_dir

    row_generator, row_count, is_truncated = stream_complaints_csv(
        snapshot=snapshot,
        filters=filters,
        q=q,
        sort_by=effective_sort,
        sort_dir=effective_order,
        max_rows=settings.EXPORT_MAX_ROWS,
    )

    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"complaints_{today_str}.csv"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Export-Truncated": "true" if is_truncated else "false",
        "X-Export-Row-Count": str(row_count),
    }

    return StreamingResponse(
        row_generator,
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/{complaint_id}", response_model=ComplaintDetailResponse)
def get_complaint(
    complaint_id: int,
    snapshot: Snapshot = Depends(get_current_snapshot),
) -> ComplaintDetailResponse:
    """
    Retrieves full detail for a single complaint record (§13.2 #10).
    Exposes extended whitelisted fields and returns 404 NOT_FOUND if ID is not found.
    """
    if complaint_id <= 0:
        raise ValidationException(
            message=f"Complaint ID must be a positive integer. Received: {complaint_id}",
            details={"complaint_id": complaint_id},
        )

    return get_complaint_detail(snapshot, complaint_id)
