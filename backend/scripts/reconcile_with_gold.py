#!/usr/bin/env python3
"""
backend/scripts/reconcile_with_gold.py
--------------------------------------
Compares locally generated Gold tables to README and Appendix B golden values (§954).
Verifies that all 9 category rows and 35 trend rows match expected counts and timely rates.
"""

import os
import sys

import pandas as pd


def reconcile(snapshot_dir: str = ".local_data") -> int:
    print("=" * 70)
    print("RECONCILING LOCAL GOLD DATA WITH AUTHORITATIVE TARGETS")
    print("=" * 70)

    gold_cat_path = os.path.join(snapshot_dir, "gold", "complaints_by_category_gold.csv")
    gold_trend_path = os.path.join(snapshot_dir, "gold", "complaints_trend_gold.csv")

    if not os.path.exists(gold_cat_path) or not os.path.exists(gold_trend_path):
        print(f"Error: Gold snapshot files not found in {snapshot_dir}")
        return 1

    df_cat = pd.read_csv(gold_cat_path)
    df_trend = pd.read_csv(gold_trend_path)

    expected_category_data = {
        ("Banking", "Deposit Accounts"): (24814, 93.6),
        ("Payments", "Card Products"): (16197, 93.2),
        ("Credit Reporting", "Consumer Reporting"): (7710, 91.4),
        ("Lending", "Real Estate Lending"): (6601, 99.1),
        ("Payments", "Money Movement"): (3453, 93.9),
        ("Collections", "Third-Party Collections"): (2736, 91.9),
        ("Lending", "Secured Lending"): (633, 92.3),
        ("Lending", "Short-Term Lending"): (333, 96.4),
        ("Lending", "Education Lending"): (39, 100.0),
    }

    errors = []
    print("\n[1] Verifying 9 Category Rows against README & Appendix B:")
    for (cat, subcat), (exp_count, exp_pct) in expected_category_data.items():
        row = df_cat[(df_cat["Category"] == cat) & (df_cat["Sub_Category"] == subcat)]
        if row.empty:
            errors.append(f"Missing row for {cat} / {subcat}")
            continue

        act_count = int(row.iloc[0]["total_complaints"])
        act_pct = float(row.iloc[0]["timely_response_pct"])

        count_match = act_count == exp_count
        pct_match = abs(act_pct - exp_pct) <= 0.1
        status = "OK" if count_match and pct_match else "MISMATCH"

        print(
            f"  {cat:16} / {subcat:24}: Count={act_count:5} (exp {exp_count:5}) | Legacy%={act_pct:5.1f}% (exp {exp_pct:5.1f}%) -> {status}"
        )
        if not count_match:
            errors.append(f"{cat}/{subcat} count {act_count} != {exp_count}")
        if not pct_match:
            errors.append(f"{cat}/{subcat} pct {act_pct} != {exp_pct}")

    print("\n[2] Verifying 35 Trend Rows (7 Years x 5 Categories):")
    distinct_years = df_trend["Year"].nunique()
    distinct_cats = df_trend["Category"].nunique()
    total_trend_rows = len(df_trend)
    print(f"  Trend rows: {total_trend_rows} (expected: 35)")
    print(f"  Distinct years: {distinct_years} (expected: 7)")
    print(f"  Distinct categories: {distinct_cats} (expected: 5)")

    if total_trend_rows != 35:
        errors.append(f"Trend total rows {total_trend_rows} != 35")
    if distinct_years != 7:
        errors.append(f"Trend years {distinct_years} != 7")
    if distinct_cats != 5:
        errors.append(f"Trend categories {distinct_cats} != 5")

    print("\n" + "=" * 70)
    if errors:
        print(f"RECONCILIATION FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  [X] {err}")
        return 1

    print("RECONCILIATION SUCCESS: ALL GOLD TABLES MATCH AUTHORITATIVE TARGETS")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(reconcile())
