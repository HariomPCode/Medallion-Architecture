# Tiny Fixture Hand-Computed Expectations

**File:** `tests/fixtures/tiny/EXPECTED.md`  
**Purpose:** Hand-computed truth values for the tiny fixture test dataset (40 records).  
**Rule:** Computed manually from `silver/ConsumerComplaints_Silver.csv` to ensure independent testing.

---

## 1. Totals & Timeliness

- **Total records:** `40`
- **Distinct Complaint IDs:** `40`
- **Duplicate IDs:** `0`
- **Timely Yes:** `32`
- **Timely No:** `4` (IDs: 1005, 1020, 1033, 1035)
- **Timeliness Unknown / Blank:** `4` (IDs: 1037, 1038, 1039, 1040)
- **Rated Cases Denominator (`timely_yes + timely_no`):** `36`
- **M-03 Primary Rate (`timely_yes / 36`):** `88.89%` (`32 / 36 * 100`)
- **M-04 Legacy Rate (`timely_yes / 40`):** `80.00%` (`32 / 40 * 100`)
- **In-Progress Cases:** `4` (IDs: 1037, 1038, 1039, 1040)

---

## 2. Categories & Sub-Categories

| Category | Sub-Category | Total | Yes | No | Blank | Legacy Rate (%) | Rated Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Banking** | Deposit Accounts | 16 | 12 | 2 | 2 | 75.0% | 85.71% |
| **Payments** | Card Products | 9 | 8 | 1 | 0 | 88.9% | 88.89% |
| **Credit Reporting** | Consumer Reporting | 6 | 6 | 0 | 0 | 100.0% | 100.00% |
| **Lending** | Real Estate Lending | 4 | 4 | 0 | 0 | 100.0% | 100.00% |
| **Payments** | Money Movement | 2 | 1 | 1 | 0 | 50.0% | 50.00% |
| **Collections** | Third-Party Collections | 2 | 0 | 0 | 2 | 0.0% | `null` (0 rated cases) |
| **Lending** | Secured Lending | 1 | 1 | 0 | 0 | 100.0% | 100.00% |

**Summary Totals by Category:**
- Banking: `16` (40.0%)
- Payments: `11` (27.5%)
- Credit Reporting: `6` (15.0%)
- Lending: `5` (12.5%)
- Collections: `2` (5.0%)
- Distinct Categories: `5`
- Distinct Sub-Categories: `7`

---

## 3. Yearly Breakdown (Date Submitted)

- **2017 (partial, starts June 1):** `4` (Banking 2, Lending 1, Payments 1)
- **2018 (complete):** `6` (Banking 2, Credit Reporting 1, Lending 1, Payments 2)
- **2019 (complete):** `6` (Banking 2, Credit Reporting 1, Lending 1, Payments 2)
- **2020 (complete):** `8` (Banking 3, Credit Reporting 2, Lending 1, Payments 2)
- **2021 (complete):** `6` (Banking 2, Credit Reporting 1, Lending 1, Payments 2)
- **2022 (complete):** `6` (Banking 3, Credit Reporting 1, Payments 2)
- **2023 (partial, through August):** `4` (Banking 2, Collections 2)

---

## 4. Anomalies

- **Flagged anomalies (`is_anomaly == True`):** `3` (IDs: 1005, 1020, 1035)
- **Normal records (`is_anomaly == False`):** `37`
- **Anomaly rate:** `7.50%` (`3 / 40 * 100`)

---

## 5. CFPB Routing Lag

- **Date submitted min/max:** `2017-06-01` to `2023-08-15`
- **Date received min/max:** `2017-06-01` to `2023-08-15`
- **Negative lags:** `0`
- **Zero lag rows:** `34` (85.0%)
- **Positive lag rows:** `6` (IDs: 1002 [1d], 1004 [5d], 1005 [30d], 1020 [30d], 1022 [2d], 1035 [20d])
