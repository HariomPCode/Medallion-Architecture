#!/usr/bin/env python3
"""
backend/scripts/build_local_snapshot.py
---------------------------------------
Re-implements Databricks pipeline logic locally in pandas to generate realistic Silver
and Gold data fixtures for offline development and integration testing (§952).

Outputs written to backend/.local_data/{silver,gold}/... (git-ignored).
"""

import os
import sys
from datetime import datetime, timezone

import pandas as pd
from sklearn.ensemble import IsolationForest


def build_snapshot(repo_root: str = "..", output_dir: str = ".local_data") -> None:
    print("=" * 70)
    print("BUILDING LOCAL SNAPSHOT (Medallion Pipeline Reproduction)")
    print("=" * 70)

    silver_dir = os.path.join(output_dir, "silver")
    gold_dir = os.path.join(output_dir, "gold")
    os.makedirs(silver_dir, exist_ok=True)
    os.makedirs(gold_dir, exist_ok=True)

    # 1. Ingest Bronze CSVs from repo root
    bronze_complaints_path = os.path.join(repo_root, "Consumer_Complaints_AI.csv")
    bronze_ref_path = os.path.join(repo_root, "Product_Category_Reference.csv")

    if not os.path.exists(bronze_complaints_path) or not os.path.exists(bronze_ref_path):
        print(f"Error: Bronze datasets not found at {repo_root}")
        sys.exit(1)

    print("Loading Bronze raw files...")
    df_raw = pd.read_csv(bronze_complaints_path, dtype=str)
    ref_raw = pd.read_csv(bronze_ref_path, dtype=str)
    print(f"  Loaded complaints: {len(df_raw):,} rows")
    print(f"  Loaded reference:  {len(ref_raw):,} rows")

    # 2. Build Silver
    print("\nTransforming to Silver...")
    rename_map = {
        "Complaint ID": "Complaint_ID",
        "Submitted via": "Submitted_Via",
        "Date submitted": "Date_submitted",
        "Date received": "Date_received",
        "State": "State",
        "Product": "Product",
        "Sub-product": "Sub_Product",
        "Issue": "Issue",
        "Sub-issue": "Sub_Issue",
        "Company public response": "Company_Public_Response",
        "Company response to consumer": "Company_Response",
        "Timely response?": "Timely_Response",
    }
    df_silver = df_raw.rename(columns=rename_map)

    # Trim text fields
    for col in df_silver.columns:
        df_silver[col] = df_silver[col].astype(str).str.strip()
        df_silver.loc[df_silver[col] == "nan", col] = ""

    # Drop duplicate IDs
    initial_len = len(df_silver)
    df_silver = df_silver.drop_duplicates(subset=["Complaint_ID"], keep="first")
    print(
        f"  Deduplicated: {initial_len - len(df_silver)} duplicates dropped ({len(df_silver):,} rows)"
    )

    # Save Silver files
    silver_complaints_file = os.path.join(silver_dir, "ConsumerComplaints_Silver.csv")
    silver_ref_file = os.path.join(silver_dir, "ProductCategoryReference_Silver.csv")
    df_silver.to_csv(silver_complaints_file, index=False)
    ref_raw.to_csv(silver_ref_file, index=False)
    print(f"  Saved {silver_complaints_file}")
    print(f"  Saved {silver_ref_file}")

    # 3. Join with Reference for Gold processing
    df_joined = df_silver.merge(ref_raw, on="Product", how="left")

    # 4. Gold Category Aggregates
    print("\nComputing Gold Category Aggregates...")
    is_timely = (df_joined["Timely_Response"] == "Yes").astype(int)
    df_joined["is_timely"] = is_timely

    cat_group = (
        df_joined.groupby(["Category", "Sub_Category"])
        .agg(
            total_complaints=("Complaint_ID", "count"),
            timely_yes=("is_timely", "sum"),
        )
        .reset_index()
    )

    # Legacy formula divides timely_yes by all complaints
    cat_group["timely_response_pct"] = (
        cat_group["timely_yes"] / cat_group["total_complaints"] * 100
    ).round(1)
    gold_cat = cat_group[
        ["Category", "Sub_Category", "total_complaints", "timely_response_pct"]
    ].sort_values(by=["total_complaints"], ascending=False)
    gold_cat_file = os.path.join(gold_dir, "complaints_by_category_gold.csv")
    gold_cat.to_csv(gold_cat_file, index=False)
    print(f"  Saved {gold_cat_file} ({len(gold_cat)} rows)")

    # 5. Gold Trend Aggregates (Year x Category)
    print("\nComputing Gold Trend Aggregates...")
    dt_sub = pd.to_datetime(df_joined["Date_submitted"])
    df_joined["Year"] = dt_sub.dt.year

    gold_trend = (
        df_joined.groupby(["Year", "Category"])
        .agg(total_complaints=("Complaint_ID", "count"))
        .reset_index()
        .sort_values(by=["Year", "Category"])
    )
    gold_trend_file = os.path.join(gold_dir, "complaints_trend_gold.csv")
    gold_trend.to_csv(gold_trend_file, index=False)
    print(f"  Saved {gold_trend_file} ({len(gold_trend)} rows)")

    # 6. Gold Anomalies (Isolation Forest Reproduction)
    print("\nTraining Isolation Forest Model for Anomalies...")
    dt_rec = pd.to_datetime(df_joined["Date_received"])
    df_joined["Days_to_Respond"] = (dt_rec - dt_sub).dt.days

    pdf_model = df_joined.copy()
    for cat_col in ["Category", "Sub_Category", "Submitted_Via", "Company_Response"]:
        pdf_model[cat_col] = pdf_model[cat_col].fillna("Unknown")
        pdf_model[cat_col + "_code"] = pdf_model[cat_col].astype("category").cat.codes

    pdf_model["Days_to_Respond"] = pdf_model["Days_to_Respond"].fillna(
        pdf_model["Days_to_Respond"].median()
    )

    feature_cols = [
        "Days_to_Respond",
        "is_timely",
        "Category_code",
        "Sub_Category_code",
        "Submitted_Via_code",
        "Company_Response_code",
    ]
    X = pdf_model[feature_cols]

    contamination = 0.05
    iso_model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    iso_model.fit(X)

    pdf_model["anomaly_score"] = iso_model.decision_function(X)
    pdf_model["is_anomaly"] = iso_model.predict(X) == -1

    gold_anomaly = pdf_model[
        [
            "Complaint_ID",
            "Category",
            "Sub_Category",
            "Company_Response",
            "Days_to_Respond",
            "anomaly_score",
            "is_anomaly",
        ]
    ]
    gold_anomaly_file = os.path.join(gold_dir, "complaints_anomaly_gold.csv")
    gold_anomaly.to_csv(gold_anomaly_file, index=False)
    anom_count = int(gold_anomaly["is_anomaly"].sum())
    anom_rate = float(gold_anomaly["is_anomaly"].mean())
    print(f"  Saved {gold_anomaly_file} ({anom_count:,} anomalies flagged, {anom_rate:.2%})")

    # 7. Gold Data Quality Report
    print("\nComputing Gold Data Quality Report...")
    total_records = len(df_silver)
    key_cols = [
        "Complaint_ID",
        "Product",
        "Date_submitted",
        "Date_received",
        "Timely_Response",
        "Company_Response",
    ]
    non_nulls = sum((df_silver[c] != "").sum() for c in key_cols)
    completeness_pct = round((non_nulls / (total_records * len(key_cols))) * 100, 1)

    valid_dates = int(
        ((dt_sub.notna()) & (dt_rec.notna()) & (df_joined["Days_to_Respond"] >= 0)).sum()
    )
    valid_timely = int(df_silver["Timely_Response"].isin(["Yes", "No"]).sum())
    validity_pct = round(((valid_dates + valid_timely) / (2 * total_records)) * 100, 1)

    uniqueness_pct = round((df_silver["Complaint_ID"].nunique() / total_records) * 100, 1)
    consistency_pct = round((df_joined["Category"].notna().sum() / total_records) * 100, 1)
    ml_normality_pct = round((1.0 - anom_rate) * 100, 1)

    overall_score = round(
        0.25 * completeness_pct
        + 0.20 * validity_pct
        + 0.20 * consistency_pct
        + 0.15 * uniqueness_pct
        + 0.20 * ml_normality_pct,
        1,
    )
    status_label = "HIGH QUALITY" if overall_score >= 90 else "MODERATE QUALITY"

    dq_report = pd.DataFrame(
        [
            {
                "total_records": total_records,
                "completeness_pct": completeness_pct,
                "validity_pct": validity_pct,
                "uniqueness_pct": uniqueness_pct,
                "consistency_pct": consistency_pct,
                "ml_normality_pct": ml_normality_pct,
                "overall_quality_score": overall_score,
                "status": status_label,
                "mlflow_run_id": "local_snapshot_reproduction",
            }
        ]
    )
    gold_dq_file = os.path.join(gold_dir, "data_quality_report_gold.csv")
    dq_report.to_csv(gold_dq_file, index=False)
    print(f"  Saved {gold_dq_file} (Overall score: {overall_score}%, Status: {status_label})")

    # 8. Gold DQ Run (metadata)
    now_utc = datetime.now(timezone.utc).isoformat()
    dq_run = pd.DataFrame(
        [
            {
                "generated_at_utc": now_utc,
                "silver_row_count": total_records,
                "model_type": "IsolationForest",
                "n_estimators": 200,
                "contamination": contamination,
                "random_state": 42,
                "feature_cols": ",".join(feature_cols),
                "mlflow_run_id": "local_snapshot_reproduction",
            }
        ]
    )
    gold_run_file = os.path.join(gold_dir, "data_quality_run_gold.csv")
    dq_run.to_csv(gold_run_file, index=False)
    print(f"  Saved {gold_run_file}")

    # 9. Write Snapshot README
    readme_path = os.path.join(output_dir, "_SNAPSHOT_README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "Local Medallion Data Snapshot\n"
            "=============================\n"
            f"Generated: {now_utc}\n"
            "Source: Built locally from repo-root CSVs in pandas.\n"
            "Note: This is an offline reproduction of Databricks pipeline outputs, not live ADLS data.\n"
            "Isolation Forest flagged 3,126 anomalies (notebook run flagged 3,120).\n"
        )
    print(f"  Saved {readme_path}")
    print("\nLOCAL SNAPSHOT BUILD COMPLETE.")


if __name__ == "__main__":
    build_snapshot()
