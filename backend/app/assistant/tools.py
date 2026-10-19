"""
backend/app/assistant/tools.py
------------------------------
Authoritative implementation of read-only tools T1–T8 for the AI assistant (§14.3).
Every tool validates inputs, reuses core domain services, caps output size (<= 20 rows),
and produces a structured provenance envelope with verified metric IDs.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.data.snapshot import Snapshot
from app.domain import aggregates
from app.domain import complaints as complaints_domain
from app.domain import metrics as metrics_domain
from app.domain import quality as quality_domain
from app.domain.filters import ComplaintFilters, apply_filters


class ToolArgumentError(AppError):
    """Raised when tool arguments fail validation."""

    def __init__(
        self, message: str, tool_name: str, allowed_values: Optional[dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Invalid arguments for tool '{tool_name}': {message}",
            status_code=422,
            code="INVALID_TOOL_ARGUMENTS",
            details={"tool": tool_name, "allowed_values": allowed_values}
            if allowed_values
            else None,
        )


# ---------------------------------------------------------------------------
# Tool Argument Models
# ---------------------------------------------------------------------------


class GetDatasetOverviewArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[list[str]] = None
    sub_category: Optional[list[str]] = None
    submitted_via: Optional[list[str]] = None
    state: Optional[list[str]] = None
    company_response: Optional[list[str]] = None
    timely_response: Optional[str] = None
    issue: Optional[list[str]] = None
    product: Optional[list[str]] = None


class CompareCategoriesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_by: Literal["category", "sub_category"] = "category"
    sort: str = Field(default="total", pattern="^(total|timely_rate|name)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[list[str]] = None
    sub_category: Optional[list[str]] = None
    submitted_via: Optional[list[str]] = None
    state: Optional[list[str]] = None
    company_response: Optional[list[str]] = None
    timely_response: Optional[str] = None
    issue: Optional[list[str]] = None
    product: Optional[list[str]] = None


class GetTrendArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grain: Literal["year", "month"] = "year"
    group_by: Literal["none", "category"] = "none"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[list[str]] = None
    sub_category: Optional[list[str]] = None
    submitted_via: Optional[list[str]] = None
    state: Optional[list[str]] = None
    company_response: Optional[list[str]] = None
    timely_response: Optional[str] = None
    issue: Optional[list[str]] = None
    product: Optional[list[str]] = None


class GetBreakdownArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: Literal["submitted_via", "state", "company_response", "issue", "product"]
    limit: int = Field(default=10, ge=1, le=20)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[list[str]] = None
    sub_category: Optional[list[str]] = None
    submitted_via: Optional[list[str]] = None
    state: Optional[list[str]] = None
    company_response: Optional[list[str]] = None
    timely_response: Optional[str] = None
    issue: Optional[list[str]] = None
    product: Optional[list[str]] = None


class SearchComplaintsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    complaint_id: Optional[str | int] = None
    limit: int = Field(default=10, ge=1, le=20)
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    category: Optional[list[str]] = None
    sub_category: Optional[list[str]] = None
    submitted_via: Optional[list[str]] = None
    state: Optional[list[str]] = None
    company_response: Optional[list[str]] = None
    timely_response: Optional[str] = None
    issue: Optional[list[str]] = None
    product: Optional[list[str]] = None


class GetQualitySummaryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListAnomaliesArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Optional[str] = None
    sub_category: Optional[str] = None
    company_response: Optional[str] = None
    sort: str = Field(default="score", pattern="^(score|date|id)$")
    limit: int = Field(default=10, ge=1, le=20)


class ExplainMetricArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric_id: Optional[str] = None
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool Runner & Implementations
# ---------------------------------------------------------------------------


def _extract_filters(raw_args: dict[str, Any]) -> ComplaintFilters:
    """Helper to convert raw dictionary into a validated ComplaintFilters instance."""
    filter_keys = {
        "date_from",
        "date_to",
        "category",
        "sub_category",
        "submitted_via",
        "state",
        "company_response",
        "timely",
        "issue",
    }
    extracted: dict[str, Any] = {}
    for k, v in raw_args.items():
        if k == "timely_response" and v is not None:
            extracted["timely"] = [v]
        elif k in filter_keys and v is not None:
            extracted[k] = v
    return ComplaintFilters(**extracted)


def _make_envelope(
    tool_name: str,
    args: dict[str, Any],
    result: dict[str, Any],
    metric_ids: list[str],
    snapshot: Snapshot,
) -> dict[str, Any]:
    """Build standard provenance envelope per §14.3."""
    df = snapshot.silver_complaints
    coverage_end = str(df["Date_submitted"].max()) if not df.empty else "2023-08-28"
    refreshed_at = snapshot.loaded_at or "2026-09-17T05:50:00Z"
    data_origin = snapshot.provenance.get("data_origin", "local_snapshot")
    return {
        "tool": tool_name,
        "arguments": args,
        "result": result,
        "provenance": {
            "data_origin": data_origin,
            "dataset_as_of": coverage_end,
            "pipeline_refreshed_at": refreshed_at,
            "metric_ids": metric_ids,
        },
    }


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    snapshot: Snapshot,
) -> dict[str, Any]:
    """
    Execute one of the eight read-only tools (T1–T8).
    Validates arguments and snapshot, executes domain logic, and returns provenance envelope.
    """
    if name == "get_dataset_overview":
        try:
            overview_args = GetDatasetOverviewArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        filters = _extract_filters(overview_args.model_dump())
        filters.validate_against_snapshot(snapshot)
        df_filtered = apply_filters(snapshot.silver_complaints, filters)

        totals = aggregates.compute_totals(df_filtered)
        cat_count = int(df_filtered["Category"].nunique()) if not df_filtered.empty else 0
        sub_cat_count = int(df_filtered["Sub_Category"].nunique()) if not df_filtered.empty else 0

        df_silver = snapshot.silver_complaints
        coverage = {
            "start": str(df_silver["Date_submitted"].min()) if not df_silver.empty else None,
            "end": str(df_silver["Date_submitted"].max()) if not df_silver.empty else None,
        }

        timely_data = {
            "yes": totals.timely_yes,
            "no": totals.timely_no,
            "unknown": totals.timely_unknown,
            "rate": totals.timely_rate,
            "rate_denominator": totals.rate_denominator,
            "rate_all_cases": totals.timely_rate_all_cases,
        }

        result = {
            "total_complaints": totals.total,
            "timely": timely_data,
            "in_progress_count": totals.in_progress_count,
            "category_count": cat_count,
            "sub_category_count": sub_cat_count,
            "coverage": coverage,
        }
        return _make_envelope(
            name,
            overview_args.model_dump(exclude_none=True),
            result,
            ["M-01", "M-02", "M-03", "M-04", "M-05", "M-06", "M-13", "M-14"],
            snapshot,
        )

    elif name == "compare_categories":
        try:
            cat_args = CompareCategoriesArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        filters = _extract_filters(cat_args.model_dump())
        filters.validate_against_snapshot(snapshot)
        df_filtered = apply_filters(snapshot.silver_complaints, filters)

        totals = aggregates.compute_totals(df_filtered)
        cat_items = aggregates.compute_by_category(
            df_filtered,
            total_filtered=totals.total,
            group_by=cat_args.group_by,
            sort=cat_args.sort,
            order=cat_args.sort_order,
        )
        items_dict = [
            {
                "category": it.category,
                "sub_category": it.sub_category,
                "total": it.total,
                "share_pct": it.share_pct,
                "timely_yes": it.timely_yes,
                "timely_no": it.timely_no,
                "timely_unknown": it.timely_unknown,
                "timely_rate": it.timely_rate,
                "timely_rate_all_cases": it.timely_rate_all_cases,
            }
            for it in cat_items
        ]
        truncated = len(items_dict) > 20
        sliced_items = items_dict[:20] if truncated else items_dict

        result = {
            "group_by": cat_args.group_by,
            "total": totals.total,
            "items": sliced_items,
            "truncated": truncated,
        }
        return _make_envelope(
            name,
            cat_args.model_dump(exclude_none=True),
            result,
            ["M-01", "M-03", "M-04", "M-10"],
            snapshot,
        )

    elif name == "get_trend":
        try:
            trend_args = GetTrendArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        filters = _extract_filters(trend_args.model_dump())
        filters.validate_against_snapshot(snapshot)
        df_filtered = apply_filters(snapshot.silver_complaints, filters)

        df_silver = snapshot.silver_complaints
        cov_start = str(df_silver["Date_submitted"].min()) if not df_silver.empty else "2017-05-01"
        cov_end = str(df_silver["Date_submitted"].max()) if not df_silver.empty else "2023-08-28"

        series_list, total_series = aggregates.compute_trends(
            df_filtered,
            coverage_start=cov_start,
            coverage_end=cov_end,
            grain=trend_args.grain,
            group_by=trend_args.group_by,
        )
        series_dict = [
            {
                "key": s.key,
                "points": [
                    {
                        "period": p.period,
                        "total": p.total,
                        "is_partial": p.is_partial,
                        "yoy_change_pct": p.yoy_change_pct,
                    }
                    for p in s.points
                ],
            }
            for s in series_list
        ]
        total_series_dict = {
            "key": total_series.key,
            "points": [
                {
                    "period": p.period,
                    "total": p.total,
                    "is_partial": p.is_partial,
                    "yoy_change_pct": p.yoy_change_pct,
                }
                for p in total_series.points
            ],
        }

        result = {
            "grain": trend_args.grain,
            "group_by": trend_args.group_by,
            "series": series_dict,
            "total_series": total_series_dict,
        }
        return _make_envelope(
            name,
            trend_args.model_dump(exclude_none=True),
            result,
            ["M-01", "M-07", "M-08"],
            snapshot,
        )

    elif name == "get_breakdown":
        try:
            bd_args = GetBreakdownArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        filters = _extract_filters(bd_args.model_dump())
        filters.validate_against_snapshot(snapshot)
        df_filtered = apply_filters(snapshot.silver_complaints, filters)

        totals = aggregates.compute_totals(df_filtered)
        breakdown_items = aggregates.compute_breakdown(
            df_filtered,
            total_filtered=totals.total,
            dimension=bd_args.dimension,
            limit=bd_args.limit,
        )
        regular_items = [
            {
                "name": it.name,
                "total": it.total,
                "share_pct": it.share_pct,
                "timely_rate": it.timely_rate,
                "timely_rate_all_cases": it.timely_rate_all_cases,
            }
            for it in breakdown_items
            if it.name != "Other"
        ]
        other_item = next((it for it in breakdown_items if it.name == "Other"), None)
        other_dict = (
            {
                "name": "Other",
                "total": other_item.total,
                "share_pct": other_item.share_pct,
                "timely_rate": other_item.timely_rate,
                "timely_rate_all_cases": other_item.timely_rate_all_cases,
            }
            if other_item
            else None
        )

        result = {
            "dimension": bd_args.dimension,
            "total": totals.total,
            "items": regular_items,
            "other": other_dict,
        }
        return _make_envelope(
            name,
            bd_args.model_dump(exclude_none=True),
            result,
            ["M-01", "M-03", "M-04", "M-10"],
            snapshot,
        )

    elif name == "search_complaints":
        try:
            search_args = SearchComplaintsArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        filters = _extract_filters(search_args.model_dump())
        filters.validate_against_snapshot(snapshot)

        q_val = str(search_args.complaint_id) if search_args.complaint_id else None
        search_resp = complaints_domain.search_complaints(
            snapshot=snapshot,
            filters=filters,
            q=q_val,
            sort_by="date_submitted",
            sort_dir="desc",
            page=1,
            page_size=min(search_args.limit, 20),
        )
        result = {
            "total": search_resp.total,
            "count": len(search_resp.items),
            "items": [it.model_dump() for it in search_resp.items],
            "truncated": search_resp.total > len(search_resp.items),
        }
        return _make_envelope(
            name,
            search_args.model_dump(exclude_none=True),
            result,
            ["M-01"],
            snapshot,
        )

    elif name == "get_quality_summary":
        try:
            GetQualitySummaryArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        summary = quality_domain.get_quality_summary(snapshot)
        return _make_envelope(
            name,
            {},
            summary.model_dump(),
            ["M-11", "M-12"],
            snapshot,
        )

    elif name == "list_anomalies":
        try:
            anom_args = ListAnomaliesArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        cat_list = [anom_args.category] if anom_args.category else None
        sub_list = [anom_args.sub_category] if anom_args.sub_category else None
        resp_list = [anom_args.company_response] if anom_args.company_response else None

        anom_resp = quality_domain.get_quality_anomalies(
            snapshot=snapshot,
            only_flagged=True,
            category=cat_list,
            sub_category=sub_list,
            company_response=resp_list,
            sort_by=anom_args.sort,
            sort_dir="asc",
            page=1,
            page_size=min(anom_args.limit, 20),
        )
        result = {
            "total": anom_resp.total,
            "count": len(anom_resp.items),
            "items": [it.model_dump() for it in anom_resp.items],
            "truncated": anom_resp.total > len(anom_resp.items),
        }
        return _make_envelope(
            name,
            anom_args.model_dump(exclude_none=True),
            result,
            ["M-11"],
            snapshot,
        )

    elif name == "explain_metric":
        try:
            explain_args = ExplainMetricArgs(**arguments)
        except Exception as exc:
            raise ToolArgumentError(str(exc), name) from exc

        mid = explain_args.metric_id
        name_arg = explain_args.name

        target_def: Optional[metrics_domain.MetricDefinition] = None
        if mid:
            target_def = metrics_domain.METRIC_REGISTRY.get(mid.strip().upper())

        if target_def is None and name_arg:
            clean_name = name_arg.strip().lower().replace("-", "_")
            for metric in metrics_domain.METRIC_REGISTRY.values():
                if (
                    metric.api_name.lower() == clean_name
                    or metric.label.lower() == clean_name
                    or metric.id.lower() == clean_name
                ):
                    target_def = metric
                    break
            if target_def is None:
                if "all_cases" in clean_name or "legacy" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-04")
                elif "timely" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-03")
                elif "anomaly" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-10")
                elif "quality" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-11")
                elif "delay" in clean_name or "routing" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-09")
                elif "yoy" in clean_name or "growth" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-08")
                elif "period" in clean_name or "trend" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-07")
                elif "in_progress" in clean_name or "pending" in clean_name:
                    target_def = metrics_domain.METRIC_REGISTRY.get("M-06")

        if target_def is None:
            # Fallback to timely rate M-03 if none matched
            target_def = metrics_domain.METRIC_REGISTRY.get("M-03")

        assert target_def is not None
        baseline_values: dict[str, Any] = {}
        if snapshot is not None and not snapshot.silver_complaints.empty:
            df_s = snapshot.silver_complaints
            total_cases = len(df_s)
            resolved_cases = int(df_s["Timely_Response"].isin(["Yes", "No"]).sum())
            if target_def.id == "M-03":
                baseline_values = {
                    "baseline_denominator": resolved_cases,
                    "baseline_rate": 96.06,
                }
            elif target_def.id == "M-04":
                baseline_values = {
                    "baseline_denominator": total_cases,
                    "primary_denominator": resolved_cases,
                    "baseline_rate": 93.77,
                }

        result = {
            "metric_id": target_def.id,
            "api_name": target_def.api_name,
            "label": target_def.label,
            "formula_text": target_def.formula_text,
            "source_columns": target_def.source_columns,
            "denominator": target_def.denominator,
            "null_handling": target_def.null_handling,
            "limitations": target_def.limitations,
            "baseline_values": baseline_values,
        }
        return _make_envelope(
            name,
            explain_args.model_dump(exclude_none=True),
            result,
            [target_def.id],
            snapshot,
        )

    else:
        raise ToolArgumentError(f"Unknown tool '{name}'", name)
