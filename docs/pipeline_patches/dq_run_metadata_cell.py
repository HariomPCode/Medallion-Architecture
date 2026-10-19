"""
docs/pipeline_patches/dq_run_metadata_cell.py
---------------------------------------------
Additive code cell to append at the end of Finance_Complaints_DataQuality_MLModel.ipynb (after cell 14).
Publishes model hyperparameters and execution timestamps to 'data_quality_run_gold.csv'.

Requirements:
- Reads variables already defined in prior notebook cells (total_rows, contamination, feature_cols, run_id).
- Does not modify any existing cell or calculation.
- Must be executed in Databricks by an operator with catalog write permissions.
"""

from datetime import datetime, timezone
import pandas as pd

# 1. Assemble single-row metadata record from notebook variables
run_metadata_pdf = pd.DataFrame([{
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "silver_row_count": total_rows,
    "model_type": "IsolationForest",
    "n_estimators": 200,
    "contamination": contamination,
    "random_state": 42,
    "feature_cols": ",".join(feature_cols),
    "mlflow_run_id": run_id,
}])

# 2. Persist to Unity Catalog / metastore table and export CSV to Gold container
df_run_metadata = spark.createDataFrame(run_metadata_pdf)
df_run_metadata.write.mode("overwrite").saveAsTable("college_project.default.data_quality_run_gold")
write_df_to_container(df_run_metadata, "gold", "data_quality_run_gold.csv")

print("[OK] Successfully published data_quality_run_gold.csv to gold container.")
