# Pipeline Patches Guide

This directory contains standalone, non-destructive patches designed to enhance pipeline metadata without altering existing data logic.

---

## Patches Summary

| Patch | Target Notebook | Action | Rationale | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`dq_run_metadata_cell.py`** | `Finance_Complaints_DataQuality_MLModel.ipynb` | Append one code cell after Cell 14 | Publishes model hyperparameters and run timestamps to `data_quality_run_gold.csv` | `READY_FOR_DATABRICKS` (`PENDING_HUMAN`) |
| **`setup_catalog_fix.md`** | `Finance Complaints ADLS Setup.ipynb` | Update table namespace in Cell 9 | Resolves catalog inconsistency A-02 (`default.*` → `college_project.default.*`) | `DOCUMENTED_ONLY` (Optional human decision) |

---

## Instructions for Applying `dq_run_metadata_cell.py`

1. Open `Finance_Complaints_DataQuality_MLModel.ipynb` in your Databricks workspace.
2. Scroll to the bottom of the notebook (after Cell 14).
3. Create a new code cell and paste the contents of [`dq_run_metadata_cell.py`](./dq_run_metadata_cell.py).
4. Run the cell.
5. Verify that `data_quality_run_gold.csv` is written to the `gold` container in your Azure Data Lake Storage account.
6. The backend automatically detects the presence of this file:
   - When present: `model.available = true`, `source = "run_metadata"`.
   - When absent: `model.available = false`, `source = "notebook_constant"`.
