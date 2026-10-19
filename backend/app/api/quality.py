"""
backend/app/api/quality.py
--------------------------
FastAPI router for Data Quality Center and Anomaly endpoints (§13.2 #12, #13).
Exposes decomposed quality metrics, audit caveats, model metadata, and annotated anomalies.
"""

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_current_snapshot
from app.core.errors import ValidationException
from app.data.snapshot import Snapshot
from app.domain.quality import get_quality_anomalies, get_quality_summary
from app.schemas.quality import AnomalyListResponse, QualitySummaryResponse

router = APIRouter(prefix="/api/v1/quality", tags=["Data Quality"])

ALLOWED_ANOMALY_PARAMS = {
    "only_flagged",
    "sort",
    "sort_by",
    "order",
    "sort_dir",
    "page",
    "page_size",
    "category",
    "sub_category",
    "company_response",
}


@router.get("/summary", response_model=QualitySummaryResponse)
def get_dq_summary(
    snapshot: Snapshot = Depends(get_current_snapshot),
) -> QualitySummaryResponse:
    """
    Retrieves composite Data Quality score, decomposed dimensions,
    model metadata, anomaly distribution, and audit caveats (§13.2 #12).
    """
    return get_quality_summary(snapshot)


@router.get("/anomalies", response_model=AnomalyListResponse)
def list_anomalies(
    request: Request,
    snapshot: Snapshot = Depends(get_current_snapshot),
    only_flagged: bool = Query(True, description="Filter only flagged anomalies"),
    sort: str | None = Query(None, description="Sort column alias ('score', 'date', 'id')"),
    sort_by: str = Query("score", description="Sort column ('score', 'date', 'id')"),
    order: str | None = Query(None, description="Sort direction alias ('asc' or 'desc')"),
    sort_dir: str = Query("asc", description="Sort direction ('asc' or 'desc')"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page (max 100)"),
) -> AnomalyListResponse:
    """
    Paginated anomaly records joined with Silver complaint fields (§13.2 #13).
    Attaches deterministic observations without fabricating ML explanations.
    """
    # 1. Enforce extra="forbid" on query parameters
    query_params = request.query_params
    unknown_params = [k for k in query_params.keys() if k not in ALLOWED_ANOMALY_PARAMS]
    if unknown_params:
        raise ValidationException(
            message=f"Unknown query parameter(s): {unknown_params}",
            details={
                "unknown_parameters": unknown_params,
                "allowed_parameters": sorted(list(ALLOWED_ANOMALY_PARAMS)),
            },
        )

    # 2. Extract multi-value filter parameters
    categories = query_params.getlist("category")
    sub_categories = query_params.getlist("sub_category")
    company_responses = query_params.getlist("company_response")

    # 3. Validate dimension values against snapshot if provided
    valid_categories = set(snapshot.silver_complaints["Category"].dropna().unique())
    invalid_cats = [c for c in categories if c not in valid_categories]
    if invalid_cats:
        raise ValidationException(
            message=f"Invalid category filter value(s): {invalid_cats}",
            details={
                "invalid_values": invalid_cats,
                "allowed_values": sorted(list(valid_categories)),
            },
        )

    valid_subcats = set(snapshot.silver_complaints["Sub_Category"].dropna().unique())
    invalid_subcats = [sc for sc in sub_categories if sc not in valid_subcats]
    if invalid_subcats:
        raise ValidationException(
            message=f"Invalid sub_category filter value(s): {invalid_subcats}",
            details={
                "invalid_values": invalid_subcats,
                "allowed_values": sorted(list(valid_subcats)),
            },
        )

    valid_responses = set(snapshot.silver_complaints["Company_Response"].dropna().unique())
    invalid_resps = [cr for cr in company_responses if cr not in valid_responses]
    if invalid_resps:
        raise ValidationException(
            message=f"Invalid company_response filter value(s): {invalid_resps}",
            details={
                "invalid_values": invalid_resps,
                "allowed_values": sorted(list(valid_responses)),
            },
        )

    effective_sort = sort if sort is not None else sort_by
    effective_order = order if order is not None else sort_dir

    return get_quality_anomalies(
        snapshot=snapshot,
        only_flagged=only_flagged,
        sort_by=effective_sort,
        sort_dir=effective_order,
        page=page,
        page_size=page_size,
        category=categories if categories else None,
        sub_category=sub_categories if sub_categories else None,
        company_response=company_responses if company_responses else None,
    )
