"""
backend/tests/unit/test_aggregates.py
------------------------------------
Unit tests for aggregation primitives, rates, YoY growth, and breakdowns (§1039, §1050, §1061).
"""

import pandas as pd

from app.domain.aggregates import (
    compute_breakdown,
    compute_by_category,
    compute_totals,
    compute_trends,
    is_month_partial,
    is_year_partial,
    rate,
)


def test_rate_helper() -> None:
    assert rate(50, 100) == 50.0
    assert rate(1, 3) == 33.33
    assert rate(2, 3) == 66.67
    assert rate(0, 100) == 0.0
    assert rate(10, 0) is None


def test_compute_totals_empty() -> None:
    df_empty = pd.DataFrame(columns=["Timely_Response", "Company_Response"])
    totals = compute_totals(df_empty)
    assert totals.total == 0
    assert totals.timely_yes == 0
    assert totals.timely_no == 0
    assert totals.timely_unknown == 0
    assert totals.rate_denominator == 0
    assert totals.timely_rate is None
    assert totals.timely_rate_all_cases is None
    assert totals.in_progress_count == 0


def test_compute_totals_with_data() -> None:
    df = pd.DataFrame(
        {
            "Timely_Response": ["Yes", "Yes", "No", None],
            "Company_Response": ["Closed", "Closed", "Closed", "In progress"],
        }
    )
    totals = compute_totals(df)
    assert totals.total == 4
    assert totals.timely_yes == 2
    assert totals.timely_no == 1
    assert totals.timely_unknown == 1
    assert totals.rate_denominator == 3
    # 2 / 3 * 100 = 66.67
    assert totals.timely_rate == 66.67
    # 2 / 4 * 100 = 50.0
    assert totals.timely_rate_all_cases == 50.0
    assert totals.in_progress_count == 1


def test_compute_by_category_grouping_and_sorting() -> None:
    df = pd.DataFrame(
        {
            "Category": ["Banking", "Banking", "Payments"],
            "Sub_Category": ["Deposit", "Deposit", "Card"],
            "Timely_Response": ["Yes", "No", "Yes"],
            "Company_Response": ["Closed", "Closed", "Closed"],
        }
    )

    items = compute_by_category(
        df, total_filtered=3, group_by="category", sort="total", order="desc"
    )
    assert len(items) == 2
    assert items[0].category == "Banking"
    assert items[0].total == 2
    assert items[0].share_pct == 66.67
    assert items[0].timely_rate == 50.0
    assert items[1].category == "Payments"
    assert items[1].total == 1
    assert items[1].share_pct == 33.33
    assert items[1].timely_rate == 100.0


def test_is_year_partial() -> None:
    # Baseline coverage: 2017-05-01 to 2023-08-28
    cov_start = "2017-05-01"
    cov_end = "2023-08-28"

    assert is_year_partial("2017", cov_start, cov_end) is True  # starts after Jan 1
    assert is_year_partial("2018", cov_start, cov_end) is False  # complete year
    assert is_year_partial("2019", cov_start, cov_end) is False  # complete year
    assert is_year_partial("2022", cov_start, cov_end) is False  # complete year
    assert is_year_partial("2023", cov_start, cov_end) is True  # ends before Dec 31


def test_is_month_partial() -> None:
    cov_start = "2017-05-01"
    cov_end = "2023-08-28"

    assert is_month_partial("2017-05", cov_start, cov_end) is False  # starts on 01
    assert is_month_partial("2023-08", cov_start, cov_end) is True  # ends on 28 (Aug has 31 days)
    assert is_month_partial("2020-02", cov_start, cov_end) is False  # Feb 2020 complete


def test_compute_trends_yoy_growth() -> None:
    # Sample spanning 2017 to 2020
    df = pd.DataFrame(
        {
            "Date_submitted": [
                "2017-06-01",  # 2017 (partial) -> 1
                "2018-01-10",
                "2018-05-20",  # 2018 (complete) -> 2
                "2019-03-15",
                "2019-07-22",
                "2019-09-01",  # 2019 (complete) -> 3
                "2020-02-14",
                "2020-04-10",
                "2020-06-18",
                "2020-11-20",
                "2020-12-05",
                "2020-12-25",  # 2020 (complete) -> 6
            ],
            "Category": ["Banking"] * 12,
        }
    )
    cov_start = "2017-05-01"
    cov_end = "2020-12-31"

    series_list, total_series = compute_trends(
        df=df,
        coverage_start=cov_start,
        coverage_end=cov_end,
        grain="year",
        group_by="none",
    )

    points = total_series.points
    assert len(points) == 4
    # 2017: partial, no prior -> yoy is None
    assert points[0].period == "2017"
    assert points[0].total == 1
    assert points[0].is_partial is True
    assert points[0].yoy_change_pct is None

    # 2018: complete, prior is partial -> yoy is None
    assert points[1].period == "2018"
    assert points[1].total == 2
    assert points[1].is_partial is False
    assert points[1].yoy_change_pct is None

    # 2019: complete, prior 2018 is complete -> (3 - 2)/2 * 100 = 50.0%
    assert points[2].period == "2019"
    assert points[2].total == 3
    assert points[2].is_partial is False
    assert points[2].yoy_change_pct == 50.0

    # 2020: complete, prior 2019 is complete -> (6 - 3)/3 * 100 = 100.0%
    assert points[3].period == "2020"
    assert points[3].total == 6
    assert points[3].is_partial is False
    assert points[3].yoy_change_pct == 100.0


def test_compute_breakdown_with_other() -> None:
    df = pd.DataFrame(
        {
            "Submitted_Via": ["Web"] * 10
            + ["Phone"] * 5
            + ["Postal"] * 3
            + ["Email"] * 2
            + ["Fax"] * 1,
            "Timely_Response": ["Yes"] * 21,
            "Company_Response": ["Closed"] * 21,
        }
    )

    # Limit to top 2
    items = compute_breakdown(df, total_filtered=21, dimension="submitted_via", limit=2)
    assert len(items) == 3  # Top 2 + Other
    assert items[0].name == "Web"
    assert items[0].total == 10
    assert items[1].name == "Phone"
    assert items[1].total == 5
    assert items[2].name == "Other"
    assert items[2].total == 6
    # Sum of items equals total
    assert sum(it.total for it in items) == 21
