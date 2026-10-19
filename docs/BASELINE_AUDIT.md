# Baseline Audit and Repository Verification

**Document:** `docs/BASELINE_AUDIT.md`  
**Execution Phase:** Phase 1 — Repository Bootstrap, Baseline Verification and Decisions  
**Date of Audit:** 2026-10-19  
**Auditor:** Autonomous Coding Agent (Pair Programming with User)  
**Status:** Complete — Golden Values Verified (0 Discrepancies)

---

## 1. Executive Summary

This document establishes the verified cryptographic, structural, and analytical baseline of the Finance Complaints Medallion repository as audited in Phase 1. 

Every existing file has been fingerprinted with SHA-256 to ensure data and notebook preservation across all future development phases. All baseline analytics metrics have been independently calculated directly from the source datasets (`Consumer_Complaints_AI.csv`, `Product_Category_Reference.csv`, and `ConsumerComplaints_DataDictionary.csv`) using `scripts/audit_baseline.py` and compared against the authoritative targets defined in `docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md` (Section 5, Section 6, and Appendix B).

**Audit Verdict:** **PASS (0 Discrepancies)**. Every golden number, category count, timely rate, sub-category distribution, and routing delay metric matches the development plan specifications to the exact integer and decimal place.

---

## 2. Repository Inventory and Asset Hashes

### 2.1 File Fingerprints (Cryptographic Baseline)

To prove that original assets remain completely untouched throughout implementation, the table below records the exact file size and SHA-256 hash for all 8 initial files:

| File Name | Size (Bytes) | SHA-256 Hash | Status |
| :--- | :--- | :--- | :--- |
| `ConsumerComplaints_DataDictionary.csv` | 1,265 | `0EF1998EEC0AFAC14106D8CE26EFBCDF20C769178222C9E5BF7B2E2DAC0DEE2A` | Verified, Preserved |
| `Consumer_Complaints_AI.csv` | 17,632,767 | `FFFD98C052DDEDCCA433AE383908FBDB9A3A950A53E90F2CBC703A2250245F49` | Verified, Preserved |
| `Finance Complaints ADLS Setup.ipynb` | 11,109,767 | `7FEF45D9F009703A7BAFF1F2B4CC447FFE998B9DEA2E5FAF2024F84CFCA5D7F9` | Verified, Preserved |
| `Finance-Gold.pbix` | 31,224 | `208B4F9FFB14CE5A20B525AE049343CCA7AE235B830ACEE2BE7CE6F71191DEF6` | Verified, Preserved |
| `Finance_Complaints_DataQuality_MLModel.ipynb` | 45,382 | `5362B90860321D429C87187765A0243B7F31F87881F5480065AA3041B5DEDC12` | Verified, Preserved |
| `Product_Category_Reference.csv` | 581 | `A18E93ABE3F343E6C501396E57738190975F184A30718E4051248C40B21E432F` | Verified, Preserved |
| `README.md` | 3,945 | `CCFC1A444B427B76D6349B75D7AB11B57D020CCC688AC9B115AE013CB1861C9E` | Verified, Preserved |
| `docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md` | 270,971 | `936DAB381DA72542F3BE7617178A209F8F194E92FCF90FB4BB5D2E025C5564A7` | Verified, Preserved |

### 2.2 Power BI Archive Structure (`Finance-Gold.pbix`)

Inspection of the Power BI report archive confirmed it contains 18 entries:
- Single report page (`Report/definition/pages/940b03dc706c864cd2c7/page.json`)
- Six visuals:
  - `78fbd08ff7dbd001ef75`
  - `9baa5733d9fde07b6560`
  - `5fab75a8a22f791f257a`
  - `6372eede942b87c314b8`
  - `e5d251eeadff535ce7de`
  - `a90c139d6b2ac04c03c2`
- Compressed DataModel (`DataModel`, 18,145 bytes) and theme settings (`Fluent2-CY26SU08.json`).
- Defect note: Visual definitions reference columns like `Banking` and `Deposit Accounts` on table `Database`, confirming the header promotion defect identified in finding A-15 of the development plan. The PBIX will not be modified.

---

## 3. Data Dictionary and Semantic Rules

Per `ConsumerComplaints_DataDictionary.csv`:

| Field Name | Data Dictionary Description | Semantic Meaning / Interpretation Rule |
| :--- | :--- | :--- |
| `Complaint ID` | The unique identification number for a complaint | Primary identifier. Integer-like string. |
| `Submitted via` | How the complaint was submitted to the CFPB | Submission channel (7 distinct categories). |
| `Date submitted` | The date the CFPB received the complaint | Date the consumer submitted and CFPB received the complaint. |
| `Date received` | The date the CFPB sent the complaint to the company | **Routing date**: Date CFPB transmitted the complaint to the institution. |
| `State` | The state of the mailing address provided by the consumer | 2-letter state code (51 distinct values). |
| `Product` | The type of product the consumer identified in the complaint | Maps 1:1 to Category and Sub-Category in reference table. |
| `Sub-product` | The type of sub-product identified (optional) | Optional refinement (7 missing records). |
| `Issue` | The issue identified in the complaint | Complaint issue category (76 distinct values). |
| `Sub-issue` | The sub-issue identified in the complaint (optional) | Detailed sub-issue (10,858 missing records, 17.37%). |
| `Company public response` | Optional public-facing company response | Preset public response options (2,175 nulls, 3.48%). |
| `Company response to consumer` | How the company responded to the consumer | Resolution category (5 distinct values). |
| `Timely response?` | Whether the company gave a timely response (Yes/No) | Timeliness flag. Recorded only for resolved cases (1,494 nulls). |

### Important Business Metric Interpretation Rules

1. **Routing Delay vs. Company Response Time (`M-09`):**  
   The difference `Date received − Date submitted` represents the **CFPB's internal routing delay** (the time elapsed between CFPB intake and routing to the financial institution). It must **NEVER** be labelled or described as "company response time". In the source data, 79.4% (49,634 rows) are routed on day 0, with a mean routing delay of 1.22 days and maximum 275 days.
2. **Timely Response Rate Denominators (`M-03` vs. `M-04`):**  
   - In `Consumer_Complaints_AI.csv`, exactly 1,494 records have a null `Timely response?`. Every one of these 1,494 cases has `Company response to consumer == "In progress"`. Their timeliness cannot be known until resolution.
   - **Primary Metric (`M-03`):** `timely_yes / (timely_yes + timely_no) * 100` = `58,619 / 61,022 = 96.06%`. Evaluates timeliness across all concluded/rated cases.
   - **Legacy Metric (`M-04`):** `timely_yes / total_complaints * 100` = `58,619 / 62,516 = 93.77%`. This reproduces the legacy Databricks/Gold/README figure (93.8%), which implicitly treats all pending in-progress cases as untimely. Both metrics will be exposed with explicit labels to avoid ambiguity.

---

## 4. Verified Baseline Analytics Metrics

All calculations below were independently executed on the raw CSV datasets using `scripts/audit_baseline.py` on 2026-10-19.

### 4.1 Dataset Dimensions and Completeness

| Metric | Result | Target (Plan §5 / App. B) | Discrepancy | Status |
| :--- | :--- | :--- | :--- | :--- |
| Total Complaint Rows | 62,516 | 62,516 | 0 | PASS |
| Total Complaint Columns | 12 | 12 | 0 | PASS |
| Distinct Complaint IDs | 62,516 | 62,516 | 0 | PASS |
| Duplicate Complaint IDs | 0 | 0 | 0 | PASS |
| `Sub-product` Null Count | 7 (0.01%) | 7 | 0 | PASS |
| `Sub-issue` Null Count | 10,858 (17.37%) | 10,858 | 0 | PASS |
| `Company public response` Null Count | 2,175 (3.48%) | 2,175 | 0 | PASS |
| `Timely response?` Null Count | 1,494 (2.39%) | 1,494 | 0 | PASS |
| All Other Columns Null Count | 0 (0.00%) | 0 | 0 | PASS |

### 4.2 Timely Response Baseline

| Metric | Formula | Result | Target (App. B) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `timely_yes` | `Timely response? == 'Yes'` | 58,619 | 58,619 | PASS |
| `timely_no` | `Timely response? == 'No'` | 2,403 | 2,403 | PASS |
| `timely_blank` / `timeliness_unknown` | `Timely response?.isna()` | 1,494 | 1,494 | PASS |
| `M-03`: `timely_response_rate` (Primary) | `58,619 / (58,619 + 2,403)` | **96.06%** | 96.06% | PASS |
| `M-04`: `timely_response_rate_all_cases` (Legacy) | `58,619 / 62,516` | **93.77%** | 93.77% | PASS |

### 4.3 In-Progress Lifecycle Cases

| Metric | Result | Target (App. B) | Status |
| :--- | :--- | :--- | :--- |
| Total `In progress` rows | 1,494 | 1,494 | PASS |
| `In progress` rows with null timeliness | 1,494 (100.0%) | 1,494 (100.0%) | PASS |
| Earliest `In progress` Date Submitted | 2023-05-12 | 2023-05-12 | PASS |
| Latest `In progress` Date Submitted | 2023-08-28 | 2023-08-28 | PASS |

### 4.4 Date Ranges and CFPB Routing Lag

| Metric | Result | Target (App. B) | Status |
| :--- | :--- | :--- | :--- |
| Date Submitted Min / Max | 2017-05-01 to 2023-08-28 | 2017-05-01 to 2023-08-28 | PASS |
| Date Received Min / Max | 2017-05-01 to 2023-08-28 | 2017-05-01 to 2023-08-28 | PASS |
| Negative Lags (`Date received < Date submitted`) | 0 | 0 | PASS |
| Zero-Day Routing Lag Count | 49,634 (79.39% ≈ 79.4%) | 49,634 (79.4%) | PASS |
| Routing Lag Mean | 1.22 days | 1.22 days | PASS |
| Routing Lag Median | 0.0 days | 0 days | PASS |
| Routing Lag Maximum | 275 days | 275 days | PASS |

### 4.5 Category and Sub-Category Breakdown

Product lookup join against `Product_Category_Reference.csv`:
- Unmatched products: **0**
- Distinct categories: **5**
- Distinct sub-categories: **9**

#### Category Totals

| Category | Total Complaints | Share (%) | Target Total | Status |
| :--- | :--- | :--- | :--- | :--- |
| Banking | 24,814 | 39.69% | 24,814 | PASS |
| Payments | 19,650 | 31.43% | 19,650 | PASS |
| Credit Reporting | 7,710 | 12.33% | 7,710 | PASS |
| Lending | 7,606 | 12.17% | 7,606 | PASS |
| Collections | 2,736 | 4.38% | 2,736 | PASS |
| **Total** | **62,516** | **100.00%** | **62,516** | **PASS** |

#### Sub-Category Totals and Timely Response Rates

| Category | Sub-Category | Total Complaints | Legacy Rate (All Cases) | Rated Timely Rate | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Banking | Deposit Accounts | 24,814 | 93.6% | 96.4% | PASS |
| Payments | Card Products | 16,197 | 93.2% | 95.6% | PASS |
| Credit Reporting | Consumer Reporting | 7,710 | 91.4% | 93.7% | PASS |
| Lending | Real Estate Lending | 6,601 | 99.1% | 99.8% | PASS |
| Payments | Money Movement | 3,453 | 93.9% | 95.9% | PASS |
| Collections | Third-Party Collections | 2,736 | 91.9% | 93.6% | PASS |
| Lending | Secured Lending | 633 | 92.3% | 94.7% | PASS |
| Lending | Short-Term Lending | 333 | 96.4% | 97.0% | PASS |
| Lending | Education Lending | 39 | 100.0% | 100.0% | PASS |

### 4.6 Yearly Volume and Year-over-Year (YoY) Trends

Complaints partitioned by year of `Date submitted`:

| Year | Banking | Collections | Credit Reporting | Lending | Payments | Total Complaints | Target Total | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2017 (partial, from May 1) | 2,039 | 287 | 466 | 1,336 | 1,266 | 5,394 | 5,394 | PASS |
| 2018 (complete) | 3,176 | 415 | 761 | 1,410 | 2,110 | 7,872 | 7,872 | PASS |
| 2019 (complete) | 3,080 | 305 | 627 | 941 | 2,122 | 7,075 | 7,075 | PASS |
| 2020 (complete) | 3,242 | 353 | 1,044 | 1,319 | 2,984 | 8,942 | 8,942 | PASS |
| 2021 (complete) | 4,006 | 671 | 1,642 | 1,147 | 3,683 | 11,149 | 11,149 | PASS |
| 2022 (complete) | 5,186 | 462 | 1,858 | 967 | 4,480 | 12,953 | 12,953 | PASS |
| 2023 (partial, to Aug 28) | 4,085 | 243 | 1,312 | 486 | 3,005 | 9,131 | 9,131 | PASS |

#### Year-over-Year Change (Complete Years Only)

Per development plan rule `M-08`, YoY is computed only when both the current and previous years represent full 12-month periods:
- **2017**: Partial (`is_partial = True`) → `YoY = null`
- **2018**: Preceding year partial → `YoY = null`
- **2019 vs 2018**: `(7,075 - 7,872) / 7,872` = **-10.12%** (Target: -10.12%) → PASS
- **2020 vs 2019**: `(8,942 - 7,075) / 7,075` = **+26.39%** (Target: +26.39%) → PASS
- **2021 vs 2020**: `(11,149 - 8,942) / 8,942` = **+24.68%** (Target: +24.68%) → PASS
- **2022 vs 2021**: `(12,953 - 11,149) / 11,149` = **+16.18%** (Target: +16.18%) → PASS
- **2023**: Partial (`is_partial = True`) → `YoY = null`

---

## 5. Pipeline & Data Quality Notebook Findings

Inspection of the committed outputs in `Finance_Complaints_DataQuality_MLModel.ipynb`:
- **Reported Data Quality Composite Score:** 98.7% (`status = "HIGH QUALITY"`).
- **Reported Dimension Breakdown:**
  - Completeness: 99.6% (penalized by the 1,494 open cases having null `Timely_Response`)
  - Validity: 98.8% (penalized by the 1,494 open cases not being strictly "Yes" or "No")
  - Uniqueness: 100.0%
  - Consistency: 100.0%
  - ML Normality: 95.0% (Derived as `1 - contamination = 1 - 0.05 = 0.95`, circular by construction)
- **Isolation Forest Model Flagged Records:** 3,120 rows (4.99%) in the original notebook output. As noted in plan finding A-08, when re-run locally with pandas null-imputation, 3,126 records are flagged, with all 1,494 *In progress* rows flagged. The model predominantly flags open cases and long CFPB routing delays rather than corrupted data.

---

## 6. Discrepancies and Limitations Summary

1. **Zero Discrepancies Against Appendix B:** All source data numbers match the plan's golden values exactly.
2. **Missing Company Names and Narratives:** The dataset does not contain company name or text narrative fields. All downstream analytics and AI capabilities are bounded to aggregated product, issue, channel, timing, and state dimensions.
3. **Partial Coverage Years:** 2017 (starts May 1) and 2023 (ends Aug 28) must always be surfaced with `is_partial = True` flags in the UI and API.
4. **Data Dictionary Character Encoding:** `ConsumerComplaints_DataDictionary.csv` begins with a UTF-8 Byte Order Mark (`\ufeff`). File readers must specify `utf-8-sig`.

---

## 7. Audit Script Execution

The baseline audit script is located at `scripts/audit_baseline.py`. It can be re-run at any time using:

```bash
python scripts/audit_baseline.py
```

The script runs in under 5 seconds on the local machine and exits with status code `0` on success.
