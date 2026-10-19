# Analytical Metrics Registry

**Document:** `docs/METRICS.md`  
**Phase:** Phase 3 — Core Analytics APIs  
**Source of Truth:** `backend/app/domain/metrics.py`  

> [!IMPORTANT]
> This document is automatically generated from the central Metric Registry in `backend/app/domain/metrics.py`.
> All REST endpoints, AI assistant tools, and dashboard visualisations must adhere to these definitions.

---

## Metric Definitions (M-01 through M-15)

| ID | API Name | Label | Formula | Denominator | Null Handling | Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M-01** | `total_complaints` | Total Complaints | `COUNT(DISTINCT Complaint_ID)` | — | Complaint_ID is unique and non-null by data contract. | Dataset is a 62,516-row extract; not the full CFPB historical database. |
| **M-02** | `category_share_pct` | Category Volume Share (%) | `(category_total / filtered_total) * 100` | filtered_total (Total complaints matching active filters) | Unmapped products assigned to 'Unmapped' category if encountered. Returns None if denominator is 0. | Shares are relative to the active filtered subset of this extract. |
| **M-03** | `timely_response_rate` | Timely Response Rate (Primary) | `(timely_yes / (timely_yes + timely_no)) * 100` | timely_yes + timely_no (Resolved cases with recorded timeliness) | Excludes open/in-progress cases with null timeliness. Returns None if denominator is 0. | Excludes 1,494 unresolved cases. Recent months contain higher proportions of pending cases. |
| **M-04** | `timely_response_rate_all_cases` | Timely Response Rate — All Cases (Legacy) | `(timely_yes / total_complaints) * 100` | total_complaints (All cases in scope, including open/unresolved cases) | Open/unresolved cases count in denominator as not timely. Returns None if total_complaints is 0. | Reproduces README/Appendix B legacy figure (93.77%). Understates compliance by penalizing active cases. |
| **M-05** | `timely_counts` | Timely Response Counts (Yes / No / Unknown) | `SUM(Timely_Response == 'Yes'), SUM(Timely_Response == 'No'), SUM(Timely_Response IS NULL)` | — | Explicitly tallies 'Unknown' / pending responses alongside Yes and No. | timely_unknown exactly equals In progress count in this dataset (1,494 records). |
| **M-06** | `in_progress_count` | In Progress Cases | `SUM(Company_Response == 'In progress')` | — | Company_Response is non-null. | Represents cases actively under review by financial institutions at time of extract (May-Aug 2023). |
| **M-07** | `complaints_by_period` | Complaints by Period (Year / Month) | `COUNT(Complaint_ID) GROUP BY Period(Date_submitted)` | — | Missing calendar periods in the range are zero-filled. Periods tagged with is_partial flag. | 2017 (starts May 1) and 2023 (ends Aug 28) are incomplete calendar years. |
| **M-08** | `yoy_change_pct` | Year-over-Year Growth (%) | `((N_current_year - N_prior_year) / N_prior_year) * 100` | N_prior_year (Complaints in preceding calendar year) | Evaluates to None if either current or prior year is partial, or if N_prior_year == 0. | Valid only between complete calendar years (2018 through 2022). Null for 2017, 2018, and 2023. |
| **M-09** | `days_submitted_to_received` | Routing Delay (CFPB to Company) | `(Date_received - Date_submitted) in days` | — | Null if either date is missing. Negative values flagged. | Measures CFPB intake and CFPB routing delay, NOT company response or resolution duration. |
| **M-10** | `anomaly_metrics` | Anomaly Score & Flags (Isolation Forest) | `IsolationForest(n_estimators=200, contamination=0.05, random_state=42)` | total_scored_records | Pre-computed in Gold layer; joined to Silver by Complaint_ID. | contamination=0.05 fixes the flagged proportion to approx 5.0% by construction. |
| **M-11** | `overall_quality_score` | Overall Data Quality Score | `0.25*Completeness + 0.20*Validity + 0.20*Consistency + 0.15*Uniqueness + 0.20*ML_Normality` | — | Pre-computed in Medallion pipeline. Evaluates to 98.7% (HIGH QUALITY). | Composite score from notebook. ML Normality is fixed by contamination parameter. |
| **M-12** | `quality_dimensions` | Data Quality Dimensions | `Five dimensions: Completeness (99.6%), Validity (98.8%), Uniqueness (100.0%), Consistency (100.0%), ML Normality (95.0%)` | — | Captured directly from pipeline report object. | Completeness/Validity are slightly reduced due to valid open cases with null timeliness. |
| **M-13** | `data_coverage` | Dataset Date Coverage | `MIN(Date_submitted) to MAX(Date_submitted)` | — | Computed from non-null Date_submitted values. | Represents business 'as-of' date range (2017-05-01 to 2023-08-28). |
| **M-14** | `pipeline_refreshed_at` | Pipeline Refresh Timestamp | `Blob/file last_modified timestamp of Silver complaints object` | — | Fallback to system snapshot load time if blob mtime unavailable. | Represents pipeline write timestamp, distinct from data coverage and quality analysis dates. |
| **M-15** | `quality_analysis_at` | Quality Analysis Timestamp | `generated_at_utc from run metadata or DQ report blob last_modified` | — | Fallback to pipeline_refreshed_at if run metadata absent. | Represents when data quality validation models were trained and scored. |

---

## Key Analytical Distinctions

### 1. Dual Timely-Response Measures (D-06)
- **Primary Rate (`M-03`):** Evaluates `timely_yes / (timely_yes + timely_no) * 100`. In our baseline: `58,619 / 61,022 = 96.06%`.
  - *Rationale:* Open cases (`In progress`) have not reached a resolution date and cannot be determined untimely prior to expiration.
- **Legacy Rate (`M-04`):** Evaluates `timely_yes / total_complaints * 100`. In our baseline: `58,619 / 62,516 = 93.77%`.
  - *Rationale:* Preserved strictly to reconcile with historical README tables and Gold outputs.

### 2. CFPB Routing Lag vs Company Response Time (M-09)
- `Date_received - Date_submitted` represents the duration CFPB took to process and forward the complaint to the financial company.
- It must **never** be labeled as 'Company Response Time' in any API, documentation, or user interface.

### 3. Partial Calendar Years (M-07 & M-08)
- **2017:** Incomplete coverage begins May 1, 2017.
- **2023:** Incomplete coverage ends August 28, 2023.
- Year-over-Year calculations (`M-08`) are strictly permitted only between complete calendar years (2018 $\to$ 2019, 2019 $\to$ 2020, 2020 $\to$ 2021, 2021 $\to$ 2022). All other years must return `null`.
