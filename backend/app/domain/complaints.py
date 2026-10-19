"""
backend/app/domain/complaints.py
--------------------------------
Domain services for Complaint Explorer and CSV Export (§13.2, §13.3).
Provides deterministic filtering, stable sorting with Complaint_ID tiebreak,
safe public field projection, and CSV formula-injection guards.
"""

import csv
import io
import math
from typing import Any, Generator, Literal

import pandas as pd

from app.core.errors import NotFoundException, ValidationException
from app.data.snapshot import Snapshot
from app.domain.filters import ComplaintFilters, apply_filters
from app.schemas.complaints import ComplaintDetailResponse, ComplaintListItem, ComplaintListResponse

SORT_COLUMN_MAPPING: dict[str, str] = {
    "date_submitted": "Date_submitted_dt",
    "complaint_id": "Complaint_ID",
    "category": "Category",
    "sub_category": "Sub_Category",
    "submitted_via": "Submitted_Via",
    "state": "State",
    "company_response": "Company_Response",
}

CSV_INJECTION_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")

EXPORT_CSV_COLUMNS: list[str] = [
    "complaint_id",
    "date_submitted",
    "category",
    "sub_category",
    "product",
    "issue",
    "submitted_via",
    "state",
    "company_response",
    "timely_response",
    "is_anomaly",
]


def sanitize_csv_cell(value: Any) -> Any:
    """
    Guards against formula injection in spreadsheet applications (§1125).
    Prefixes a single quote to string values beginning with =, +, -, @, \\t, or \\r.
    """
    if isinstance(value, str):
        if value and value[0] in CSV_INJECTION_PREFIXES:
            return f"'{value}"
    return value


def _to_bool_series(s: pd.Series) -> pd.Series:
    """Safely converts string or boolean series to boolean mask."""
    return s.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "t"])


def _parse_bool(val: Any) -> bool:
    """Safely parses scalar string or boolean value to bool."""
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "t")


def validate_complaint_id_query(q: str | None) -> int | None:
    """
    Validates the 'q' search parameter.
    Must consist of digits only (up to 12 chars). Raises 422 if invalid.
    """
    if q is None:
        return None
    cleaned = q.strip()
    if not cleaned:
        return None
    if not cleaned.isdigit() or len(cleaned) > 12:
        raise ValidationException(
            message=f"Search query 'q' must consist of digits only (up to 12 characters). Received: '{q}'",
            details={"q": q},
        )
    return int(cleaned)


def _apply_sorting_and_filtering(
    snapshot: Snapshot,
    filters: ComplaintFilters,
    q: str | None = None,
    sort_by: str = "date_submitted",
    sort_dir: str = "desc",
) -> pd.DataFrame:
    """Applies common filters, query ID filter, and deterministic sorting."""
    df = snapshot.silver_complaints

    # 1. Apply shared filters
    df = apply_filters(df, filters)

    # 2. Apply 'q' exact ID filter if provided
    numeric_id = validate_complaint_id_query(q)
    if numeric_id is not None:
        df = df[df["Complaint_ID"].astype(str) == str(numeric_id)]

    # 3. Validate sort column and direction
    sort_key = sort_by.lower()
    if sort_key not in SORT_COLUMN_MAPPING:
        allowed = sorted(list(SORT_COLUMN_MAPPING.keys()))
        raise ValidationException(
            message=f"Invalid sort column '{sort_by}'. Allowed columns: {allowed}",
            details={"sort_by": sort_by, "allowed_columns": allowed},
        )

    order_key = sort_dir.lower()
    if order_key not in ("asc", "desc"):
        raise ValidationException(
            message=f"Invalid sort direction '{sort_dir}'. Must be 'asc' or 'desc'.",
            details={"sort_dir": sort_dir},
        )

    sort_col = SORT_COLUMN_MAPPING[sort_key]
    ascending = order_key == "asc"

    # 4. Stable deterministic sorting with numeric secondary tie-break on Complaint_ID desc
    df = df.copy()
    df["_cid_num"] = pd.to_numeric(df["Complaint_ID"], errors="coerce")
    if sort_col == "Complaint_ID":
        df = df.sort_values(by=["_cid_num"], ascending=[ascending])
    else:
        df = df.sort_values(by=[sort_col, "_cid_num"], ascending=[ascending, False])
    df = df.drop(columns=["_cid_num"])

    return df


def _normalize_timely(value: Any) -> Literal["yes", "no"] | None:
    if pd.isna(value) or value is None:
        return None
    s = str(value).strip().lower()
    if s == "yes":
        return "yes"
    elif s == "no":
        return "no"
    return None


def _format_list_item(row: pd.Series, anomaly_map: dict[int, bool] | None) -> ComplaintListItem:
    complaint_id = int(row["Complaint_ID"])
    is_anom: bool | None = None
    if anomaly_map is not None:
        is_anom = anomaly_map.get(complaint_id)

    state_val = row.get("State")
    state_str = str(state_val) if pd.notna(state_val) and state_val != "" else None

    return ComplaintListItem(
        complaint_id=complaint_id,
        date_submitted=str(row["Date_submitted"]),
        category=str(row["Category"]),
        sub_category=str(row["Sub_Category"]),
        product=str(row["Product"]),
        issue=str(row["Issue"]),
        submitted_via=str(row["Submitted_Via"]),
        state=state_str,
        company_response=str(row["Company_Response"]),
        timely_response=_normalize_timely(row.get("Timely_Response")),
        is_anomaly=is_anom,
    )


def search_complaints(
    snapshot: Snapshot,
    filters: ComplaintFilters,
    q: str | None = None,
    sort_by: str = "date_submitted",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> ComplaintListResponse:
    """
    Retrieves paginated, filtered, and deterministically sorted complaints (§13.2 #9).
    Exposes only public whitelisted fields and joins anomaly status.
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

    df = _apply_sorting_and_filtering(
        snapshot=snapshot,
        filters=filters,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    total = len(df)
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    offset = (page - 1) * page_size
    if offset >= total:
        page_df = df.iloc[0:0]
    else:
        page_df = df.iloc[offset : offset + page_size]

    # Build anomaly lookup for this page's complaint IDs
    anomaly_map: dict[int, bool] | None = None
    if snapshot.gold_anomaly is not None and not snapshot.gold_anomaly.empty:
        page_ids = set(page_df["Complaint_ID"].astype(str).unique())
        anom_slice = snapshot.gold_anomaly[
            snapshot.gold_anomaly["Complaint_ID"].astype(str).isin(page_ids)
        ]
        anomaly_map = dict(
            zip(
                pd.to_numeric(anom_slice["Complaint_ID"], errors="coerce").astype(int),
                _to_bool_series(anom_slice["is_anomaly"]),
            )
        )

    items = [_format_list_item(row, anomaly_map) for _, row in page_df.iterrows()]

    return ComplaintListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


def get_complaint_detail(snapshot: Snapshot, complaint_id: int) -> ComplaintDetailResponse:
    """
    Retrieves full record for a single complaint (§13.2 #10).
    Raises 404 NOT_FOUND if the ID does not exist in the snapshot.
    """
    df = snapshot.silver_complaints
    matches = df[df["Complaint_ID"].astype(str) == str(complaint_id)]
    if matches.empty:
        raise NotFoundException(
            message=f"Complaint ID {complaint_id} was not found.",
            details={"complaint_id": complaint_id},
        )

    row = matches.iloc[0]

    # Join anomaly details if present
    is_anom: bool | None = None
    anom_score: float | None = None
    if snapshot.gold_anomaly is not None and not snapshot.gold_anomaly.empty:
        anom_matches = snapshot.gold_anomaly[
            snapshot.gold_anomaly["Complaint_ID"].astype(str) == str(complaint_id)
        ]
        if not anom_matches.empty:
            anom_row = anom_matches.iloc[0]
            is_anom = _parse_bool(anom_row["is_anomaly"])
            if pd.notna(anom_row.get("anomaly_score")):
                anom_score = float(anom_row["anomaly_score"])

    # Optional fields
    date_rec = str(row["Date_received"]) if pd.notna(row.get("Date_received")) else None
    routing_lag: int | None = None
    if pd.notna(row.get("days_submitted_to_received")):
        routing_lag = int(row["days_submitted_to_received"])

    sub_prod = (
        str(row["Sub_Product"])
        if pd.notna(row.get("Sub_Product")) and row["Sub_Product"] != ""
        else None
    )
    sub_iss = (
        str(row["Sub_Issue"]) if pd.notna(row.get("Sub_Issue")) and row["Sub_Issue"] != "" else None
    )
    pub_resp = (
        str(row["Company_Public_Response"])
        if pd.notna(row.get("Company_Public_Response")) and row["Company_Public_Response"] != ""
        else None
    )
    state_val = str(row["State"]) if pd.notna(row.get("State")) and row["State"] != "" else None

    return ComplaintDetailResponse(
        complaint_id=complaint_id,
        date_submitted=str(row["Date_submitted"]),
        date_received=date_rec,
        days_submitted_to_received=routing_lag,
        category=str(row["Category"]),
        sub_category=str(row["Sub_Category"]),
        product=str(row["Product"]),
        sub_product=sub_prod,
        issue=str(row["Issue"]),
        sub_issue=sub_iss,
        submitted_via=str(row["Submitted_Via"]),
        state=state_val,
        company_response=str(row["Company_Response"]),
        company_public_response=pub_resp,
        timely_response=_normalize_timely(row.get("Timely_Response")),
        is_anomaly=is_anom,
        anomaly_score=anom_score,
    )


def stream_complaints_csv(
    snapshot: Snapshot,
    filters: ComplaintFilters,
    q: str | None = None,
    sort_by: str = "date_submitted",
    sort_dir: str = "desc",
    max_rows: int = 10_000,
) -> tuple[Generator[str, None, None], int, bool]:
    """
    Streams filtered, sorted complaint records as CSV (§13.2 #11).
    Enforces EXPORT_MAX_ROWS capping, sets truncation status, and applies formula injection guard.
    Returns: (generator, row_count, is_truncated)
    """
    df = _apply_sorting_and_filtering(
        snapshot=snapshot,
        filters=filters,
        q=q,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    total_matching = len(df)
    is_truncated = total_matching > max_rows
    export_df = df.iloc[:max_rows] if is_truncated else df
    row_count = len(export_df)

    # Anomaly lookup
    anomaly_map: dict[int, bool] | None = None
    if snapshot.gold_anomaly is not None and not snapshot.gold_anomaly.empty:
        export_ids = set(export_df["Complaint_ID"].astype(str).unique())
        anom_slice = snapshot.gold_anomaly[
            snapshot.gold_anomaly["Complaint_ID"].astype(str).isin(export_ids)
        ]
        anomaly_map = dict(
            zip(
                pd.to_numeric(anom_slice["Complaint_ID"], errors="coerce").astype(int),
                _to_bool_series(anom_slice["is_anomaly"]),
            )
        )

    def row_generator() -> Generator[str, None, None]:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # 1. Header row
        writer.writerow(EXPORT_CSV_COLUMNS)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        # 2. Data rows
        for _, row in export_df.iterrows():
            cid = int(row["Complaint_ID"])
            is_anom: bool | None = None
            if anomaly_map is not None:
                is_anom = anomaly_map.get(cid)

            timely = _normalize_timely(row.get("Timely_Response"))
            state_val = row.get("State")
            state_str = str(state_val) if pd.notna(state_val) and state_val != "" else ""

            row_values = [
                cid,
                sanitize_csv_cell(str(row["Date_submitted"])),
                sanitize_csv_cell(str(row["Category"])),
                sanitize_csv_cell(str(row["Sub_Category"])),
                sanitize_csv_cell(str(row["Product"])),
                sanitize_csv_cell(str(row["Issue"])),
                sanitize_csv_cell(str(row["Submitted_Via"])),
                sanitize_csv_cell(state_str),
                sanitize_csv_cell(str(row["Company_Response"])),
                timely if timely is not None else "",
                is_anom if is_anom is not None else "",
            ]
            writer.writerow(row_values)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return row_generator(), row_count, is_truncated
