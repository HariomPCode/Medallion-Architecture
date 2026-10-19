"""
backend/app/domain/aggregates.py
--------------------------------
Authoritative aggregation primitives and analytical calculations (§1038, §1050, §1061).
Encapsulates single rate calculations, dual timeliness rates, data-driven partial-year detection,
YoY comparisons, and breakdown bucket aggregations.
"""

import calendar
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

import pandas as pd


def round_half_up(val: float, decimals: int = 2) -> float:
    """Half-up decimal rounding to eliminate floating point imprecision."""
    d = Decimal(str(val))
    return float(d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP))


def rate(numerator: int, denominator: int) -> float | None:
    """
    Single authoritative rate helper per §1039.
    Returns None if denominator is zero; otherwise returns percentage rounded to 2 decimal places.
    """
    if denominator == 0:
        return None
    val = (numerator / denominator) * 100.0
    return round_half_up(val, 2)


@dataclass(frozen=True)
class AggregatedTotals:
    """Total complaint counts, dual timely rates, and in-progress counts."""

    total: int
    timely_yes: int
    timely_no: int
    timely_unknown: int
    rate_denominator: int
    timely_rate: float | None
    timely_rate_all_cases: float | None
    in_progress_count: int


def compute_totals(df: pd.DataFrame) -> AggregatedTotals:
    """Computes basic total volume and timely metrics on a (filtered) complaints DataFrame."""
    total = len(df)
    if total == 0:
        return AggregatedTotals(
            total=0,
            timely_yes=0,
            timely_no=0,
            timely_unknown=0,
            rate_denominator=0,
            timely_rate=None,
            timely_rate_all_cases=None,
            in_progress_count=0,
        )

    timely_yes = int((df["Timely_Response"] == "Yes").sum())
    timely_no = int((df["Timely_Response"] == "No").sum())
    timely_unknown = int(df["Timely_Response"].isna().sum())
    rate_denom = timely_yes + timely_no

    timely_rate = rate(timely_yes, rate_denom)
    timely_rate_all = rate(timely_yes, total)
    in_progress = int((df["Company_Response"] == "In progress").sum())

    return AggregatedTotals(
        total=total,
        timely_yes=timely_yes,
        timely_no=timely_no,
        timely_unknown=timely_unknown,
        rate_denominator=rate_denom,
        timely_rate=timely_rate,
        timely_rate_all_cases=timely_rate_all,
        in_progress_count=in_progress,
    )


@dataclass(frozen=True)
class CategorySummaryItem:
    """Category or sub-category volume, share, and timeliness breakdown."""

    category: str
    sub_category: str | None
    total: int
    share_pct: float | None
    timely_yes: int
    timely_no: int
    timely_unknown: int
    timely_rate: float | None
    timely_rate_all_cases: float | None


def compute_by_category(
    df: pd.DataFrame,
    total_filtered: int,
    group_by: Literal["category", "sub_category"] = "category",
    sort: str = "total",
    order: str = "desc",
) -> list[CategorySummaryItem]:
    """
    Computes volume and timely metrics aggregated by Category or Sub_Category (§1050).
    Omits categories with 0 complaints in the filtered set.
    """
    if df.empty or total_filtered == 0:
        return []

    items: list[CategorySummaryItem] = []

    if group_by == "category":
        for cat_key, cat_df in df.groupby("Category", observed=True):
            tot = compute_totals(cat_df)
            share = rate(tot.total, total_filtered)
            items.append(
                CategorySummaryItem(
                    category=str(cat_key),
                    sub_category=None,
                    total=tot.total,
                    share_pct=share,
                    timely_yes=tot.timely_yes,
                    timely_no=tot.timely_no,
                    timely_unknown=tot.timely_unknown,
                    timely_rate=tot.timely_rate,
                    timely_rate_all_cases=tot.timely_rate_all_cases,
                )
            )
    else:
        # group_by == "sub_category"
        for sub_key, sub_df in df.groupby(["Category", "Sub_Category"], observed=True):
            cat_name = str(sub_key[0]) if isinstance(sub_key, tuple) else str(sub_key)
            sub_name = str(sub_key[1]) if isinstance(sub_key, tuple) and len(sub_key) > 1 else None
            tot = compute_totals(sub_df)
            share = rate(tot.total, total_filtered)
            items.append(
                CategorySummaryItem(
                    category=cat_name,
                    sub_category=sub_name,
                    total=tot.total,
                    share_pct=share,
                    timely_yes=tot.timely_yes,
                    timely_no=tot.timely_no,
                    timely_unknown=tot.timely_unknown,
                    timely_rate=tot.timely_rate,
                    timely_rate_all_cases=tot.timely_rate_all_cases,
                )
            )

    # Sort whitelist: "total", "timely_rate", "name"
    reverse = order.lower() == "desc"

    def sort_key(item: CategorySummaryItem) -> tuple[Any, ...]:
        name_val = item.sub_category if group_by == "sub_category" else item.category
        if sort == "timely_rate":
            # For nulls in rates, sort them to the end when descending
            val = item.timely_rate if item.timely_rate is not None else -1.0
            return (val, name_val)
        elif sort == "name":
            return (name_val,)
        else:
            # Default: "total"
            return (item.total, name_val)

    items.sort(key=sort_key, reverse=reverse)
    return items


@dataclass(frozen=True)
class TrendPoint:
    """A single period's volume and growth point in a trend series."""

    period: str
    total: int
    is_partial: bool
    yoy_change_pct: float | None


@dataclass(frozen=True)
class TrendSeries:
    """A named time-series of points."""

    key: str
    points: list[TrendPoint]


def is_month_partial(period_str: str, coverage_start: str, coverage_end: str) -> bool:
    """
    Determines if a YYYY-MM period is partial based on global snapshot coverage.
    Month is partial if coverage starts later than 1st of that month or ends before last day of that month.
    """
    year, month = map(int, period_str.split("-"))
    _, last_day = calendar.monthrange(year, month)
    first_date_str = f"{period_str}-01"
    last_date_str = f"{period_str}-{last_day:02d}"

    if coverage_start > first_date_str:
        return True
    if coverage_end < last_date_str:
        return True
    return False


def is_year_partial(period_str: str, coverage_start: str, coverage_end: str) -> bool:
    """
    Determines if a YYYY period is partial based on global snapshot coverage.
    Year is partial if coverage starts after Jan 1 or ends before Dec 31.
    """
    first_date_str = f"{period_str}-01-01"
    last_date_str = f"{period_str}-12-31"

    if coverage_start > first_date_str:
        return True
    if coverage_end < last_date_str:
        return True
    return False


def compute_trends(
    df: pd.DataFrame,
    coverage_start: str,
    coverage_end: str,
    grain: Literal["year", "month"] = "year",
    group_by: Literal["none", "category"] = "none",
) -> tuple[list[TrendSeries], TrendSeries]:
    """
    Computes time-series complaint trends per §1061.
    Zero-fills missing periods within the active date span.
    Computes YoY growth only between non-partial, complete periods.
    """
    # 1. Determine period range from active data or global coverage
    start_dt = df["Date_submitted"].min() if not df.empty else coverage_start
    end_dt = df["Date_submitted"].max() if not df.empty else coverage_end

    if grain == "year":
        start_period = start_dt[:4]
        end_period = end_dt[:4]
        all_periods = [str(y) for y in range(int(start_period), int(end_period) + 1)]
    else:
        # month grain
        start_year, start_month = int(start_dt[:4]), int(start_dt[5:7])
        end_year, end_month = int(end_dt[:4]), int(end_dt[5:7])
        all_periods = []
        cur_y, cur_m = start_year, start_month
        while (cur_y < end_year) or (cur_y == end_year and cur_m <= end_month):
            all_periods.append(f"{cur_y:04d}-{cur_m:02d}")
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1

    def build_points_for_subset(sub_df: pd.DataFrame) -> list[TrendPoint]:
        if sub_df.empty:
            period_counts: dict[str, int] = {p: 0 for p in all_periods}
        else:
            if grain == "year":
                series = sub_df["Date_submitted"].str[:4].value_counts()
            else:
                series = sub_df["Date_submitted"].str[:7].value_counts()
            period_counts = {p: int(series.get(p, 0)) for p in all_periods}

        points: list[TrendPoint] = []
        prior_point: TrendPoint | None = None

        for period in all_periods:
            tot = period_counts[period]
            if grain == "year":
                partial = is_year_partial(period, coverage_start, coverage_end)
            else:
                partial = is_month_partial(period, coverage_start, coverage_end)

            # YoY calculation per M-08
            yoy: float | None = None
            if prior_point is not None:
                if not partial and not prior_point.is_partial and prior_point.total > 0:
                    yoy = rate(tot - prior_point.total, prior_point.total)

            pt = TrendPoint(
                period=period,
                total=tot,
                is_partial=partial,
                yoy_change_pct=yoy,
            )
            points.append(pt)
            prior_point = pt

        return points

    # Build total series
    total_points = build_points_for_subset(df)
    total_series = TrendSeries(key="Total", points=total_points)

    series_list: list[TrendSeries] = []
    if group_by == "none":
        series_list.append(total_series)
    else:
        # group_by == "category"
        # Determine categories (only include categories present in the filtered set or non-empty)
        categories = sorted(df["Category"].dropna().unique().tolist()) if not df.empty else []
        for cat in categories:
            cat_df = df[df["Category"] == cat]
            cat_points = build_points_for_subset(cat_df)
            series_list.append(TrendSeries(key=cat, points=cat_points))

    return series_list, total_series


@dataclass(frozen=True)
class BreakdownItem:
    """A single dimension slice in a top-N breakdown."""

    name: str
    total: int
    share_pct: float | None
    timely_rate: float | None
    timely_rate_all_cases: float | None


def compute_breakdown(
    df: pd.DataFrame,
    total_filtered: int,
    dimension: Literal["submitted_via", "state", "company_response", "issue", "product"],
    limit: int = 10,
) -> list[BreakdownItem]:
    """
    Computes Top-N breakdown by dimension with an 'Other' bucket so all items sum to total (§1062).
    """
    if df.empty or total_filtered == 0:
        return []

    col_map = {
        "submitted_via": "Submitted_Via",
        "state": "State",
        "company_response": "Company_Response",
        "issue": "Issue",
        "product": "Product",
    }
    col_name = col_map[dimension]

    grouped = df.groupby(col_name, observed=True)
    stats_list = []
    for val, g in grouped:
        tot = compute_totals(g)
        stats_list.append((str(val), tot))

    # Sort descending by total, then by name
    stats_list.sort(key=lambda x: (x[1].total, x[0]), reverse=True)

    items: list[BreakdownItem] = []
    top_entries = stats_list[:limit]
    remaining_entries = stats_list[limit:]

    for name_str, tot in top_entries:
        items.append(
            BreakdownItem(
                name=name_str,
                total=tot.total,
                share_pct=rate(tot.total, total_filtered),
                timely_rate=tot.timely_rate,
                timely_rate_all_cases=tot.timely_rate_all_cases,
            )
        )

    if remaining_entries:
        # Aggregate other
        other_total = sum(t.total for _, t in remaining_entries)
        other_yes = sum(t.timely_yes for _, t in remaining_entries)
        other_no = sum(t.timely_no for _, t in remaining_entries)
        other_denom = other_yes + other_no

        items.append(
            BreakdownItem(
                name="Other",
                total=other_total,
                share_pct=rate(other_total, total_filtered),
                timely_rate=rate(other_yes, other_denom),
                timely_rate_all_cases=rate(other_yes, other_total),
            )
        )

    return items
