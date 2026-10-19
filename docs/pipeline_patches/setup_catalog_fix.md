# Setup Catalog Three-Part Name Fix (Optional / Human Decision)

**Reference:** Finding A-02 (`docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md` §2.3 and §1151).  
**Target File:** `Finance Complaints ADLS Setup.ipynb` (Cell 9).  
**Status:** `DOCUMENTED_ONLY` (Requires human review before modifying repository notebooks).

---

## 1. Problem Description

In `Finance Complaints ADLS Setup.ipynb`, Silver tables are written in Cell 9 using two-part catalog names:
```python
df_silver.write.mode("overwrite").saveAsTable("default.consumercomplaints_silver")
df_ref_silver.write.mode("overwrite").saveAsTable("default.productcategoryreference_silver")
```

However, downstream cells in both `Finance Complaints ADLS Setup.ipynb` (Cells 10–12) and `Finance_Complaints_DataQuality_MLModel.ipynb` (Cells 4, 10, 14) query and save tables using three-part Unity Catalog names:
```python
spark.read.table("college_project.default.consumercomplaints_silver")
spark.read.table("college_project.default.productcategoryreference_silver")
```

This causes an execution error if the active Databricks session's default catalog is not set to `college_project`.

---

## 2. Proposed Patch

In Cell 9 of `Finance Complaints ADLS Setup.ipynb`, replace the table names with the explicit three-part identifier:

```python
# Before:
df_silver.write.mode("overwrite").saveAsTable("default.consumercomplaints_silver")
df_ref_silver.write.mode("overwrite").saveAsTable("default.productcategoryreference_silver")

# After:
df_silver.write.mode("overwrite").saveAsTable("college_project.default.consumercomplaints_silver")
df_ref_silver.write.mode("overwrite").saveAsTable("college_project.default.productcategoryreference_silver")
```

---

## 3. Human Decision Policy

- Per **D-07** and **AC-4.6**, existing repository notebooks must not be modified automatically by coding agents.
- This patch is documented here for execution by authorized data engineers in the Databricks workspace.
