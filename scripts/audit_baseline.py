#!/usr/bin/env python3
"""
scripts/audit_baseline.py
-------------------------
Reproducible baseline audit script for the Finance Complaints Medallion repository.
Validates datasets against Appendix B Golden Values from docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md.

Exits with code 0 if all baseline checks pass, 1 if any check fails.
"""

from decimal import Decimal, ROUND_HALF_UP
import os
import sys
import pandas as pd


def round_half_up(val: float, decimals: int = 2) -> float:
    """Standard half-up rounding for metric comparisons."""
    d = Decimal(str(val))
    return float(d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP))


def run_audit(base_dir: str = ".") -> int:
    print("=" * 80)
    print("FINANCE COMPLAINTS MEDALLION — REPRODUCIBLE BASELINE AUDIT")
    print("=" * 80)

    # 1. File existence validation
    required_files = [
        "Consumer_Complaints_AI.csv",
        "Product_Category_Reference.csv",
        "ConsumerComplaints_DataDictionary.csv",
        "Finance Complaints ADLS Setup.ipynb",
        "Finance_Complaints_DataQuality_MLModel.ipynb",
        "Finance-Gold.pbix",
        "README.md",
    ]

    print("\n[1] Checking Required Repository Files...")
    missing_files = []
    for f in required_files:
        p = os.path.join(base_dir, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            print(f"  [OK] {f:45} ({size:,} bytes)")
        else:
            print(f"  [FAIL] Missing file: {f}")
            missing_files.append(f)

    if missing_files:
        print(f"\nAudit failed: missing required files: {missing_files}")
        return 1

    # 2. Dataset loading (memory-conscious string loading)
    print("\n[2] Loading Datasets...")
    complaints_path = os.path.join(base_dir, "Consumer_Complaints_AI.csv")
    reference_path = os.path.join(base_dir, "Product_Category_Reference.csv")
    dictionary_path = os.path.join(base_dir, "ConsumerComplaints_DataDictionary.csv")

    df = pd.read_csv(complaints_path, dtype=str)
    ref = pd.read_csv(reference_path, dtype=str)
    data_dict = pd.read_csv(dictionary_path, encoding="utf-8-sig")

    total_rows = len(df)
    total_cols = len(df.columns)
    print(f"  Loaded Consumer_Complaints_AI.csv: {total_rows:,} rows, {total_cols} columns")
    print(f"  Loaded Product_Category_Reference.csv: {len(ref)} rows, {len(ref.columns)} columns")
    print(f"  Loaded ConsumerComplaints_DataDictionary.csv: {len(data_dict)} rows")

    failures = []

    # 3. Golden Values Verification: Totals & Uniqueness
    print("\n[3] Verifying Complaint Identifiers and Volume...")
    distinct_ids = df["Complaint ID"].nunique()
    duplicate_ids = total_rows - distinct_ids
    print(f"  Total records: {total_rows} (expected: 62,516)")
    print(f"  Distinct Complaint IDs: {distinct_ids} (expected: 62,516)")
    print(f"  Duplicate IDs: {duplicate_ids} (expected: 0)")

    if total_rows != 62516:
        failures.append(f"Total rows {total_rows} != 62516")
    if distinct_ids != 62516 or duplicate_ids != 0:
        failures.append(f"Duplicate IDs found: {duplicate_ids}")

    # 4. Nulls and Completeness
    print("\n[4] Column Null and Empty Counts:")
    expected_nulls = {
        "Complaint ID": 0,
        "Submitted via": 0,
        "Date submitted": 0,
        "Date received": 0,
        "State": 0,
        "Product": 0,
        "Sub-product": 7,
        "Issue": 0,
        "Sub-issue": 10858,
        "Company public response": 2175,
        "Company response to consumer": 0,
        "Timely response?": 1494,
    }

    for col in df.columns:
        null_count = int(df[col].isna().sum() + (df[col] == "").sum())
        pct = (null_count / total_rows) * 100
        exp = expected_nulls.get(col)
        status = "OK" if exp is None or null_count == exp else "MISMATCH"
        print(f"  - {col:30}: {null_count:6} nulls ({pct:5.2f}%) [expected: {exp}] -> {status}")
        if exp is not None and null_count != exp:
            failures.append(f"Column '{col}' null count {null_count} != expected {exp}")

    # 5. Timely Response Metrics (M-03 vs M-04)
    print("\n[5] Timely Response Metrics:")
    timely_yes = int((df["Timely response?"] == "Yes").sum())
    timely_no = int((df["Timely response?"] == "No").sum())
    timely_blank = int(df["Timely response?"].isna().sum() + (df["Timely response?"] == "").sum())
    rated_denominator = timely_yes + timely_no

    m03_rated_rate = (timely_yes / rated_denominator) * 100
    m04_legacy_rate = (timely_yes / total_rows) * 100

    print(f"  Timely Yes: {timely_yes:,} (expected: 58,619)")
    print(f"  Timely No:  {timely_no:,} (expected: 2,403)")
    print(f"  Timely Blank: {timely_blank:,} (expected: 1,494)")
    print(f"  M-03 Primary Rate (Yes / Rated): {m03_rated_rate:.2f}% (expected: 96.06%)")
    print(f"  M-04 Legacy Rate (Yes / All):   {m04_legacy_rate:.2f}% (expected: 93.77%)")

    if timely_yes != 58619:
        failures.append(f"Timely Yes count {timely_yes} != 58619")
    if timely_no != 2403:
        failures.append(f"Timely No count {timely_no} != 2403")
    if timely_blank != 1494:
        failures.append(f"Timely Blank count {timely_blank} != 1494")
    if round_half_up(m03_rated_rate, 2) != 96.06:
        failures.append(f"M-03 rate {m03_rated_rate:.4f}% != 96.06%")
    if round_half_up(m04_legacy_rate, 2) != 93.77:
        failures.append(f"M-04 rate {m04_legacy_rate:.4f}% != 93.77%")

    # 6. In-Progress Cases Analysis
    print("\n[6] In-Progress Case Verification:")
    in_progress_mask = df["Company response to consumer"] == "In progress"
    in_progress_count = int(in_progress_mask.sum())
    in_progress_timely_null = int(df.loc[in_progress_mask, "Timely response?"].isna().sum())
    in_progress_min_date = df.loc[in_progress_mask, "Date submitted"].min()
    in_progress_max_date = df.loc[in_progress_mask, "Date submitted"].max()

    print(f"  'In progress' count: {in_progress_count} (expected: 1,494)")
    print(f"  'In progress' rows with null timeliness: {in_progress_timely_null} (expected: 1,494)")
    print(f"  'In progress' submission dates: {in_progress_min_date} to {in_progress_max_date} (expected: 2023-05-12 to 2023-08-28)")

    if in_progress_count != 1494:
        failures.append(f"In-progress count {in_progress_count} != 1494")
    if in_progress_timely_null != 1494:
        failures.append(f"In-progress null timeliness {in_progress_timely_null} != 1494")
    if in_progress_min_date != "2023-05-12" or in_progress_max_date != "2023-08-28":
        failures.append(f"In-progress date range mismatch: {in_progress_min_date} to {in_progress_max_date}")

    # 7. Dates and Routing Delay (Lag)
    print("\n[7] Dates and CFPB Routing Lag:")
    dt_sub = pd.to_datetime(df["Date submitted"])
    dt_rec = pd.to_datetime(df["Date received"])
    lag = (dt_rec - dt_sub).dt.days

    sub_min = df["Date submitted"].min()
    sub_max = df["Date submitted"].max()
    rec_min = df["Date received"].min()
    rec_max = df["Date received"].max()

    negative_lags = int((lag < 0).sum())
    zero_lags = int((lag == 0).sum())
    zero_lag_pct = (zero_lags / total_rows) * 100
    mean_lag = lag.mean()
    median_lag = lag.median()
    max_lag = lag.max()

    print(f"  Date submitted range: {sub_min} to {sub_max} (expected: 2017-05-01 to 2023-08-28)")
    print(f"  Date received range:  {rec_min} to {rec_max} (expected: 2017-05-01 to 2023-08-28)")
    print(f"  Negative lags: {negative_lags} (expected: 0)")
    print(f"  Zero-day routing lag: {zero_lags:,} ({zero_lag_pct:.1f}%) (expected: 49,634 / 79.4%)")
    print(f"  Lag statistics: mean={mean_lag:.2f}, median={median_lag:.1f}, max={max_lag} (expected: 1.22 / 0 / 275)")

    if sub_min != "2017-05-01" or sub_max != "2023-08-28":
        failures.append(f"Date submitted range mismatch: {sub_min} to {sub_max}")
    if rec_min != "2017-05-01" or rec_max != "2023-08-28":
        failures.append(f"Date received range mismatch: {rec_min} to {rec_max}")
    if negative_lags != 0:
        failures.append(f"Found {negative_lags} negative lags")
    if zero_lags != 49634:
        failures.append(f"Zero-lag count {zero_lags} != 49634")
    if round_half_up(mean_lag, 2) != 1.22:
        failures.append(f"Mean lag {mean_lag:.4f} != 1.22")
    if median_lag != 0:
        failures.append(f"Median lag {median_lag} != 0")
    if max_lag != 275:
        failures.append(f"Max lag {max_lag} != 275")

    # 8. Product Reference Join and Categories
    print("\n[8] Product Reference Join & Category Verification:")
    merged = df.merge(ref, on="Product", how="left")
    unmatched_products = int(merged["Category"].isna().sum())
    distinct_categories = int(merged["Category"].nunique())
    distinct_subcategories = int(merged["Sub_Category"].nunique())

    print(f"  Unmatched products: {unmatched_products} (expected: 0)")
    print(f"  Distinct categories: {distinct_categories} (expected: 5)")
    print(f"  Distinct sub-categories: {distinct_subcategories} (expected: 9)")

    if unmatched_products != 0:
        failures.append(f"Unmatched products: {unmatched_products}")
    if distinct_categories != 5:
        failures.append(f"Distinct categories {distinct_categories} != 5")
    if distinct_subcategories != 9:
        failures.append(f"Distinct sub-categories {distinct_subcategories} != 9")

    # Category totals comparison
    expected_categories = {
        "Banking": 24814,
        "Payments": 19650,
        "Credit Reporting": 7710,
        "Lending": 7606,
        "Collections": 2736,
    }
    print("  Category Volume Verification:")
    for cat, exp_count in expected_categories.items():
        actual_count = int((merged["Category"] == cat).sum())
        status = "OK" if actual_count == exp_count else "MISMATCH"
        print(f"    - {cat:18}: {actual_count:6} (expected: {exp_count:6}) -> {status}")
        if actual_count != exp_count:
            failures.append(f"Category '{cat}' volume {actual_count} != expected {exp_count}")

    # Sub-category totals and rates
    expected_subcategories = {
        ("Banking", "Deposit Accounts"): (24814, 93.6, 96.4),
        ("Payments", "Card Products"): (16197, 93.2, 95.6),
        ("Credit Reporting", "Consumer Reporting"): (7710, 91.4, 93.7),
        ("Lending", "Real Estate Lending"): (6601, 99.1, 99.8),
        ("Payments", "Money Movement"): (3453, 93.9, 95.9),
        ("Collections", "Third-Party Collections"): (2736, 91.9, 93.6),
        ("Lending", "Secured Lending"): (633, 92.3, 94.7),
        ("Lending", "Short-Term Lending"): (333, 96.4, 97.0),
        ("Lending", "Education Lending"): (39, 100.0, 100.0),
    }

    print("\n  Sub-Category Totals and Timely Rates Verification:")
    for (cat, subcat), (exp_tot, exp_legacy, exp_rated) in expected_subcategories.items():
        subset = merged[(merged["Category"] == cat) & (merged["Sub_Category"] == subcat)]
        actual_tot = len(subset)
        sub_yes = (subset["Timely response?"] == "Yes").sum()
        sub_no = (subset["Timely response?"] == "No").sum()
        actual_legacy = round_half_up((sub_yes / actual_tot) * 100, 1)
        actual_rated = round_half_up((sub_yes / (sub_yes + sub_no)) * 100, 1) if (sub_yes + sub_no) > 0 else 0.0

        tot_ok = actual_tot == exp_tot
        legacy_ok = actual_legacy == exp_legacy
        rated_ok = actual_rated == exp_rated
        status = "OK" if tot_ok and legacy_ok and rated_ok else "MISMATCH"
        print(f"    - {cat:16} / {subcat:23}: tot={actual_tot:5} (exp {exp_tot:5}), legacy={actual_legacy:5.1f}% (exp {exp_legacy:5.1f}%), rated={actual_rated:5.1f}% (exp {exp_rated:5.1f}%) -> {status}")

        if not tot_ok:
            failures.append(f"Subcategory ({cat}, {subcat}) total {actual_tot} != {exp_tot}")
        if not legacy_ok:
            failures.append(f"Subcategory ({cat}, {subcat}) legacy rate {actual_legacy}% != {exp_legacy}%")
        if not rated_ok:
            failures.append(f"Subcategory ({cat}, {subcat}) rated rate {actual_rated}% != {exp_rated}%")

    # 9. Yearly Counts and YoY
    print("\n[9] Yearly Volume and YoY Changes:")
    merged["Year"] = dt_sub.dt.year
    expected_years = {
        2017: 5394,
        2018: 7872,
        2019: 7075,
        2020: 8942,
        2021: 11149,
        2022: 12953,
        2023: 9131,
    }
    for yr, exp_yr_tot in expected_years.items():
        actual_yr_tot = int((merged["Year"] == yr).sum())
        status = "OK" if actual_yr_tot == exp_yr_tot else "MISMATCH"
        print(f"    - Year {yr}: {actual_yr_tot:6} (expected: {exp_yr_tot:6}) -> {status}")
        if actual_yr_tot != exp_yr_tot:
            failures.append(f"Year {yr} total {actual_yr_tot} != {exp_yr_tot}")

    expected_yoy = {
        2019: -10.12,
        2020: 26.39,
        2021: 24.68,
        2022: 16.18,
    }
    for yr, exp_pct in expected_yoy.items():
        prev_yr_tot = expected_years[yr - 1]
        curr_yr_tot = expected_years[yr]
        calc_pct = round_half_up(((curr_yr_tot - prev_yr_tot) / prev_yr_tot) * 100, 2)
        status = "OK" if calc_pct == exp_pct else "MISMATCH"
        print(f"    - YoY {yr} vs {yr-1}: {calc_pct:+6.2f}% (expected: {exp_pct:+6.2f}%) -> {status}")
        if calc_pct != exp_pct:
            failures.append(f"YoY {yr} change {calc_pct}% != expected {exp_pct}%")

    print("\n" + "=" * 80)
    if failures:
        print(f"AUDIT FAILED WITH {len(failures)} DISCREPANCIES:")
        for fail in failures:
            print(f"  [X] {fail}")
        return 1
    else:
        print("AUDIT SUCCESS: ALL BASELINE METRICS REPRODUCED EXACTLY (0 DISCREPANCIES)")
        print("=" * 80)
        return 0


if __name__ == "__main__":
    sys.exit(run_audit())
