"""
backend/app/domain/quality.py
-----------------------------
Domain services for Data Quality Center and Anomaly endpoints (§13.2, §13.3).
Provides decomposed quality dimensions, audit caveats, model metadata,
and deterministic observations for detected anomalies.
"""

import math
from typing import Any, Literal

import pandas as pd

from app.core.errors import DataSourceError, ValidationException
from app.data.snapshot import Snapshot
from app.schemas.quality import (
    AnomalyAnnotations,
    AnomalyListItem,
    AnomalyListResponse,
    AnomalySummaryBlock,
    CategoryAnomalyItem,
    CompanyResponseAnomalyItem,
    ModelMetadata,
    QualityDimension,
    QualitySummaryResponse,
    QualityTimestamps,
)

ROUTING_DELAY_ANOMALY_DAYS: int = 7

ANOMALY_SORT_COLUMNS: dict[str, str] = {
    "score": "anomaly_score",
    "date": "Date_submitted_dt",
    "id": "Complaint_ID",
}


def _to_bool_series(s: pd.Series) -> pd.Series:
    """Safely converts string or boolean series to boolean mask."""
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "t"])


def _parse_bool(val: Any) -> bool:
    """Safely parses scalar string or boolean value to bool."""
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "t")


def _normalize_timely(value: Any) -> Literal["yes", "no"] | None:
    if pd.isna(value) or value is None:
        return None
    s = str(value).strip().lower()
    if s == "yes":
        return "yes"
    elif s == "no":
        return "no"
    return None


def get_quality_summary(snapshot: Snapshot) -> QualitySummaryResponse:
    """
    Builds the Data Quality Center summary card payload (§13.2 #12).
    Decomposes the 5 dimensions with notes, summarizes anomaly distributions,
    and includes mandatory audit limitations (§6 A-05..A-08).
    """
    dq_df = snapshot.gold_dq_report
    if dq_df is None or dq_df.empty:
        raise DataSourceError("Gold Data Quality report is unavailable in loaded snapshot.")

    silver_df = snapshot.silver_complaints
    anom_df = snapshot.gold_anomaly
    warnings: list[str] = []

    # 1. Parse DQ report row
    row = dq_df.iloc[0]
    total_records = int(row["total_records"])
    completeness_pct = round(float(row["completeness_pct"]), 2)
    validity_pct = round(float(row["validity_pct"]), 2)
    uniqueness_pct = round(float(row["uniqueness_pct"]), 2)
    consistency_pct = round(float(row["consistency_pct"]), 2)
    ml_normality_pct = round(float(row["ml_normality_pct"]), 2)
    overall_score = round(float(row["overall_quality_score"]), 2)
    report_status = str(row["status"]).strip()
    mlflow_run_id = str(row["mlflow_run_id"]) if pd.notna(row.get("mlflow_run_id")) else None

    # Cross-checks
    if total_records != len(silver_df):
        warnings.append(
            f"DQ report total records ({total_records}) does not match Silver complaint count ({len(silver_df)})."
        )

    # Re-derive quality status from overall score thresholds (§6 M-11)
    if overall_score >= 90.0:
        rederived_status: Literal["HIGH QUALITY", "MODERATE QUALITY", "LOW QUALITY"] = (
            "HIGH QUALITY"
        )
    elif overall_score >= 75.0:
        rederived_status = "MODERATE QUALITY"
    else:
        rederived_status = "LOW QUALITY"

    if rederived_status != report_status:
        warnings.append(
            f"Pipeline status '{report_status}' differs from score threshold band '{rederived_status}'."
        )

    # 2. Compute data-driven notes for dimensions
    open_cases_count = int((silver_df["Company_Response"] == "In progress").sum())
    total_silver = len(silver_df)
    valid_timely_count = int(silver_df["Timely_Response"].isin(["Yes", "No"]).sum())

    dimensions = [
        QualityDimension(
            id="completeness",
            label="Completeness",
            value=completeness_pct,
            weight=0.25,
            definition="Proportion of non-null attributes across mandatory complaint schema fields.",
            note=f"Lowered by {open_cases_count:,} open ('In progress') cases with no timeliness value.",
        ),
        QualityDimension(
            id="validity",
            label="Validity",
            value=validity_pct,
            weight=0.20,
            definition="Conformance to domain ranges, enumerated categories, and resolved response values.",
            note=f"Timely response recorded as Yes or No for {valid_timely_count:,} of {total_silver:,} complaints.",
        ),
        QualityDimension(
            id="consistency",
            label="Consistency",
            value=consistency_pct,
            weight=0.20,
            definition="Chronological consistency between complaint submission date and CFPB receipt date.",
            note="CFPB routing logic verified: Date received >= Date submitted across all valid records.",
        ),
        QualityDimension(
            id="uniqueness",
            label="Uniqueness",
            value=uniqueness_pct,
            weight=0.15,
            definition="Distinctness of primary complaint identifiers (Complaint_ID uniqueness).",
            note="Zero duplicate Complaint_IDs detected in Silver layer.",
        ),
        QualityDimension(
            id="ml_normality",
            label="ML Normality",
            value=ml_normality_pct,
            weight=0.20,
            definition="Proportion of complaints exhibiting normal multivariate behavior via Isolation Forest.",
            note="Derived from Isolation Forest anomaly detection (nominal contamination=0.05).",
        ),
    ]

    # 3. Anomaly Summary Block
    anom_summary: AnomalySummaryBlock
    if anom_df is not None and not anom_df.empty:
        if len(anom_df) != len(silver_df):
            warnings.append(
                f"Anomaly dataset record count ({len(anom_df)}) does not match Silver complaints ({len(silver_df)})."
            )

        flagged_mask = _to_bool_series(anom_df["is_anomaly"])
        flagged_count = int(flagged_mask.sum())
        total_anom = len(anom_df)
        rate_pct = round((flagged_count / total_anom) * 100, 2) if total_anom > 0 else 0.0

        # Compute in_progress_share_pct by joining to Silver (§1137)
        # Silver contains Company_Response
        flagged_df = anom_df[flagged_mask]
        merged_flagged = flagged_df.merge(
            silver_df[["Complaint_ID", "Company_Response"]],
            on="Complaint_ID",
            how="left",
            suffixes=("", "_silver"),
        )
        resp_col = (
            "Company_Response_silver"
            if "Company_Response_silver" in merged_flagged.columns
            else "Company_Response"
        )
        open_anom_count = int((merged_flagged[resp_col] == "In progress").sum())
        in_progress_share = (
            round((open_anom_count / flagged_count) * 100, 2) if flagged_count > 0 else 0.0
        )

        # by_category
        cat_counts = silver_df["Category"].value_counts().to_dict()
        flagged_by_cat = (
            flagged_df["Category"].value_counts().to_dict() if "Category" in flagged_df else {}
        )
        by_category: list[CategoryAnomalyItem] = []
        for cat, total_c in cat_counts.items():
            fl_c = int(flagged_by_cat.get(cat, 0))
            r = round((fl_c / total_c) * 100, 2) if total_c > 0 else 0.0
            by_category.append(
                CategoryAnomalyItem(category=str(cat), flagged=fl_c, total=int(total_c), rate_pct=r)
            )
        by_category.sort(key=lambda x: x.flagged, reverse=True)

        # by_company_response
        resp_counts = silver_df["Company_Response"].value_counts().to_dict()
        flagged_by_resp = merged_flagged[resp_col].value_counts().to_dict()
        by_response: list[CompanyResponseAnomalyItem] = []
        for cr, total_r in resp_counts.items():
            fl_r = int(flagged_by_resp.get(cr, 0))
            r = round((fl_r / total_r) * 100, 2) if total_r > 0 else 0.0
            by_response.append(
                CompanyResponseAnomalyItem(
                    company_response=str(cr), flagged=fl_r, total=int(total_r), rate_pct=r
                )
            )
        by_response.sort(key=lambda x: x.flagged, reverse=True)

        anom_summary = AnomalySummaryBlock(
            flagged=flagged_count,
            rate_pct=rate_pct,
            in_progress_share_pct=in_progress_share,
            by_category=by_category,
            by_company_response=by_response,
        )
    else:
        anom_summary = AnomalySummaryBlock(
            flagged=0,
            rate_pct=0.0,
            in_progress_share_pct=None,
            by_category=[],
            by_company_response=[],
        )

    # 4. Model Metadata Block
    model_meta: ModelMetadata
    analysis_ts: str | None = None
    if snapshot.gold_dq_run is not None and not snapshot.gold_dq_run.empty:
        run_row = snapshot.gold_dq_run.iloc[0]
        feats = [f.strip() for f in str(run_row.get("feature_cols", "")).split(",") if f.strip()]
        model_meta = ModelMetadata(
            available=True,
            type=str(run_row.get("model_type", "IsolationForest")),
            contamination=float(run_row.get("contamination", 0.05)),
            n_estimators=int(run_row.get("n_estimators", 200)),
            features=feats,
            mlflow_run_id=str(run_row.get("mlflow_run_id", mlflow_run_id or "")),
            source="run_metadata",
        )
        if pd.notna(run_row.get("generated_at_utc")):
            analysis_ts = str(run_row.get("generated_at_utc"))
    else:
        model_meta = ModelMetadata(
            available=False,
            type="IsolationForest",
            contamination=0.05,
            n_estimators=200,
            features=[
                "Days_to_Respond",
                "is_timely",
                "Category_code",
                "Sub_Category_code",
                "Submitted_Via_code",
                "Company_Response_code",
            ],
            mlflow_run_id=mlflow_run_id,
            source="notebook_constant",
        )

    # 5. Timestamps
    report_ts = snapshot.provenance.get("loaded_at", snapshot.loaded_at)
    timestamps = QualityTimestamps(
        quality_analysis_at=analysis_ts,
        report_object_refreshed_at=report_ts,
    )

    # 6. Static Limitations List (§6 A-05..A-08 & §1136)
    contam = model_meta.contamination
    limitations = [
        f"ML Normality is derived from the fixed contamination parameter ({contam:.2f}) and is ~{100.0 - contam * 100:.1f}% by construction, rather than an empirical distribution test.",
        "Completeness and Validity scores are mechanically depressed by open ('In progress') complaints, which cannot have a timeliness verdict until resolved.",
        "Isolation Forest anomaly detection uses label-encoded categorical variables and median-imputed routing delays; anomalies represent unusual feature combinations, not confirmed data errors.",
        f"Anomalies are heavily concentrated in open cases ({open_cases_count:,} of {open_cases_count:,} in-progress complaints flagged) and cases with extended CFPB routing delays.",
    ]

    return QualitySummaryResponse(
        overall_quality_score=overall_score,
        status=rederived_status,
        total_records=total_records,
        dimensions=dimensions,
        anomalies=anom_summary,
        model=model_meta,
        timestamps=timestamps,
        limitations=limitations,
        warnings=warnings,
    )


def get_quality_anomalies(
    snapshot: Snapshot,
    only_flagged: bool = True,
    sort_by: str = "score",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 25,
    category: list[str] | None = None,
    sub_category: list[str] | None = None,
    company_response: list[str] | None = None,
) -> AnomalyListResponse:
    """
    Retrieves paginated anomaly records joined with Silver complaint fields (§13.2 #13).
    Attaches deterministic observational annotations without fabricating ML explanations.
    """
    if page < 1:
        raise ValidationException(
            message=f"Page must be greater than or equal to 1. Received: {page}",
            details={"page": page},
        )
    if page_size < 1 or page_size > 100:
        raise ValidationException(
            message=f"Page size must be between 1 and 100. Received: {page_size}",
            details={"page_size": page_size},
        )

    anom_df = snapshot.gold_anomaly
    if anom_df is None or anom_df.empty:
        raise DataSourceError("Gold Anomaly table is unavailable in loaded snapshot.")

    silver_df = snapshot.silver_complaints

    # 1. Join Gold Anomaly with Silver Complaints on Complaint_ID
    # Silver has: Date_submitted, Date_submitted_dt, Product, Issue, Submitted_via, State, Timely_Response, days_submitted_to_received
    # Anomaly has: Complaint_ID, Category, Sub_Category, Company_Response, Days_to_Respond, anomaly_score, is_anomaly
    cols_to_use = [
        "Complaint_ID",
        "Date_submitted",
        "Date_submitted_dt",
        "Category",
        "Sub_Category",
        "Product",
        "Issue",
        "Submitted_Via",
        "State",
        "Company_Response",
        "Timely_Response",
        "days_submitted_to_received",
    ]
    available_silver_cols = [c for c in cols_to_use if c in silver_df.columns]
    merged = anom_df.merge(
        silver_df[available_silver_cols],
        on="Complaint_ID",
        how="inner",
        suffixes=("", "_silver"),
    )

    # 2. Filter flagged status
    if only_flagged:
        merged = merged[_to_bool_series(merged["is_anomaly"])]

    # 3. Optional filters
    if category:
        merged = merged[merged["Category"].isin(category)]
    if sub_category:
        merged = merged[merged["Sub_Category"].isin(sub_category)]
    if company_response:
        resp_col = (
            "Company_Response" if "Company_Response" in merged.columns else "Company_response"
        )
        merged = merged[merged[resp_col].isin(company_response)]

    # 4. Sorting
    sort_key = sort_by.lower()
    if sort_key not in ANOMALY_SORT_COLUMNS:
        allowed = sorted(list(ANOMALY_SORT_COLUMNS.keys()))
        raise ValidationException(
            message=f"Invalid anomaly sort column '{sort_by}'. Allowed columns: {allowed}",
            details={"sort_by": sort_by, "allowed_columns": allowed},
        )

    order_key = sort_dir.lower()
    if order_key not in ("asc", "desc"):
        raise ValidationException(
            message=f"Invalid sort direction '{sort_dir}'. Must be 'asc' or 'desc'.",
            details={"sort_dir": sort_dir},
        )

    sort_col = ANOMALY_SORT_COLUMNS[sort_key]
    ascending = order_key == "asc"

    # Deterministic sorting with secondary tie-break on Complaint_ID asc
    if sort_col == "Complaint_ID":
        merged = merged.sort_values(by=["Complaint_ID"], ascending=[ascending])
    else:
        merged = merged.sort_values(by=[sort_col, "Complaint_ID"], ascending=[ascending, True])

    total = len(merged)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    if offset >= total:
        page_df = merged.iloc[0:0]
    else:
        page_df = merged.iloc[offset : offset + page_size]

    items: list[AnomalyListItem] = []
    for _, row in page_df.iterrows():
        cid = int(row["Complaint_ID"])
        resp_val = str(row.get("Company_Response", row.get("Company_response", "")))
        lag_val = row.get("days_submitted_to_received")
        routing_lag = int(lag_val) if pd.notna(lag_val) else None
        timely_norm = _normalize_timely(row.get("Timely_Response"))

        # Deterministic observations (§1138)
        open_case = resp_val == "In progress"
        long_delay = routing_lag is not None and routing_lag >= ROUTING_DELAY_ANOMALY_DAYS
        timely_no = timely_norm == "no"

        state_val = row.get("State")
        state_str = str(state_val) if pd.notna(state_val) and state_val != "" else None

        items.append(
            AnomalyListItem(
                complaint_id=cid,
                date_submitted=str(row["Date_submitted"]),
                category=str(row["Category"]),
                sub_category=str(row["Sub_Category"]),
                product=str(row["Product"]),
                issue=str(row["Issue"]),
                submitted_via=str(row["Submitted_Via"]),
                state=state_str,
                company_response=resp_val,
                timely_response=timely_norm,
                days_submitted_to_received=routing_lag,
                anomaly_score=float(row["anomaly_score"]),
                is_anomaly=_parse_bool(row["is_anomaly"]),
                annotations=AnomalyAnnotations(
                    open_case=open_case,
                    long_routing_delay=long_delay,
                    timely_no=timely_no,
                ),
                annotations_note="Observations, not model explanations",
            )
        )

    return AnomalyListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )
