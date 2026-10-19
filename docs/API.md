# Backend API Specification

**Document:** `docs/API.md`  
**Phase:** Phase 5 — Grounded AI Assistant Backend  
**Base URL:** `/api/v1`  
**Schema Definition:** [`docs/openapi.json`](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/docs/openapi.json)  

All endpoints communicate exclusively via JSON over HTTPS. All field names use `snake_case`. Every response includes an `X-Request-ID` header.

---

## 1. Global Conventions & Error Envelope

### Standard Error Envelope

When any error occurs (HTTP 4xx or 5xx), the backend returns a uniform, sanitized error payload:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "date_from ('2023-01-01') must be less than or equal to date_to ('2022-01-01').",
    "details": {},
    "request_id": "993fa91a-7b3b-4b21-a5d6-ec2d7b5b5c90"
  }
}
```

#### Standard Error Codes:
- `VALIDATION_ERROR` (HTTP 422): Malformed parameters, out-of-range dates, or unrecognized filter values.
- `NOT_FOUND` (HTTP 404): Requested entity or resource not found.
- `DATA_UNAVAILABLE` (HTTP 503): No valid data snapshot loaded in memory.
- `INTERNAL_ERROR` (HTTP 500): Sanitized internal server failure (no stack traces or internals disclosed).

### Common Query Filters

Applicable to `/dashboard/summary`, `/analytics/by-category`, `/analytics/trends`, `/analytics/breakdown`, `/analytics/kpis`:

| Parameter | Type | Validation Rules | Description |
| :--- | :--- | :--- | :--- |
| `category` | Repeatable string | Must exist in loaded snapshot; $\le 20$ values | Filter by high-level category (e.g. `Banking`) |
| `sub_category` | Repeatable string | Must exist in loaded snapshot; $\le 20$ values | Filter by sub-category (e.g. `Deposit Accounts`) |
| `submitted_via` | Repeatable string | Must exist in loaded snapshot; $\le 20$ values | Channel (e.g. `Web`, `Referral`, `Phone`) |
| `state` | Repeatable string | Must exist in loaded snapshot; $\le 20$ values | US State abbreviation (e.g. `CA`, `NY`) |
| `company_response`| Repeatable string | Must exist in loaded snapshot; $\le 20$ values | Company response outcome |
| `timely` | Repeatable enum | `yes`, `no`, `unknown`; $\le 20$ values | Response timeliness status |
| `issue` | Repeatable string | Must exist in loaded snapshot; $\le 20$ values | Specific complaint issue text |
| `date_from` | String (`YYYY-MM-DD`)| Must be valid ISO date $\le date\_to$ | Filter complaints submitted on or after date |
| `date_to` | String (`YYYY-MM-DD`)| Must be valid ISO date $\ge date\_from$ | Filter complaints submitted on or before date |

Unrecognized query parameters return `422 VALIDATION_ERROR` (`extra="forbid"`).

---

## 2. Endpoints Inventory

### 2.1 Health & Liveness

#### `GET /health/live`
- **Purpose:** Process liveness probe.
- **Response:** HTTP 200 with `{"status": "alive", "app_env": "local", "request_id": "..."}`.

#### `GET /health/ready`
- **Purpose:** Readiness probe verifying that a validated data snapshot is loaded in memory.
- **Response:** HTTP 200 with `{"status": "ready", "data_status": "fresh", "row_count": 62516, ...}`. Returns HTTP 503 if snapshot is unavailable or failing validation.

---

### 2.2 Metadata Endpoints

#### `GET /api/v1/meta/dataset`
- **Purpose:** Dataset provenance, record counts, coverage dates, skew status, and timestamps.
- **Parameters:** None.
- **Response Schema:** `DatasetMetaResponse`
```json
{
  "data_origin": "local_snapshot",
  "data_status": "fresh",
  "total_silver_records": 62516,
  "row_counts": {
    "silver_complaints": 62516,
    "product_reference": 9,
    "gold_category": 9,
    "gold_trend": 35,
    "gold_anomaly": 62516
  },
  "coverage": {
    "start": "2017-05-01",
    "end": "2023-08-28"
  },
  "pipeline_refreshed_at": "2026-10-19T11:00:00Z",
  "quality_analysis_at": null,
  "skew_warning": false,
  "schema_version": "1.0.0",
  "warnings": []
}
```

#### `GET /api/v1/meta/filters`
- **Purpose:** Dimension hierarchies and allowed values for client-side filter population.
- **Parameters:** None.
- **Response Schema:** `FiltersMetaResponse`
- **Fields:** `categories` (name + sub_categories list), `submitted_via`, `state`, `company_response`, `timely`, `issues`, `coverage`.

---

### 2.3 Dashboard & KPI Endpoints

#### `GET /api/v1/dashboard/summary` and `GET /api/v1/analytics/kpis`
- **Purpose:** Key performance indicator strip and total complaint metrics.
- **Parameters:** Common query filters.
- **Response Schema:** `DashboardSummaryResponse`
```json
{
  "filters_applied": {
    "category": [],
    "sub_category": [],
    "submitted_via": [],
    "state": [],
    "company_response": [],
    "timely": [],
    "issue": [],
    "date_from": null,
    "date_to": null
  },
  "total_complaints": 62516,
  "timely": {
    "yes": 58619,
    "no": 2403,
    "unknown": 1494,
    "rate": 96.06,
    "rate_denominator": 61022,
    "rate_all_cases": 93.77
  },
  "in_progress_count": 1494,
  "category_count": 5,
  "sub_category_count": 9,
  "coverage": {
    "start": "2017-05-01",
    "end": "2023-08-28"
  },
  "pipeline_refreshed_at": "2026-10-19T11:00:00Z",
  "data_origin": "local_snapshot"
}
```

---

### 2.4 Analytics Endpoints

#### `GET /api/v1/analytics/by-category` (and alias `/api/v1/analytics/categories`)
- **Purpose:** Aggregated complaint volume, volume share, and dual timely response rates grouped by Category or Sub_Category.
- **Parameters:**
  - `group_by`: `category` (default) or `sub_category`.
  - `sort`: `total` (default), `timely_rate`, or `name`.
  - `order`: `desc` (default) or `asc`.
  - Common query filters.
- **Response Schema:** `ByCategoryResponse`
```json
{
  "group_by": "category",
  "total": 62516,
  "items": [
    {
      "category": "Banking",
      "sub_category": null,
      "total": 24814,
      "share_pct": 39.69,
      "timely_yes": 23215,
      "timely_no": 857,
      "timely_unknown": 742,
      "timely_rate": 96.44,
      "timely_rate_all_cases": 93.56
    }
  ],
  "filters_applied": { ... }
}
```

#### `GET /api/v1/analytics/trends`
- **Purpose:** Time-series volume trends with data-driven partial-period detection and YoY growth.
- **Parameters:**
  - `grain`: `year` (default) or `month`.
  - `group_by`: `none` (default) or `category`.
  - Common query filters.
- **Response Schema:** `TrendsResponse`
- **Business Rule:** `yoy_change_pct` evaluates to `null` if either current or preceding period is partial (`is_partial == true`) or prior volume is 0.

#### `GET /api/v1/analytics/breakdown`
- **Purpose:** Top-N volume breakdown along a selected dimension with an `Other` remainder bucket.
- **Parameters:**
  - `dimension`: `submitted_via`, `state`, `company_response`, `issue`, or `product` (Required).
  - `limit`: Integer between 1 and 50 (default 10).
  - Common query filters.
- **Response Schema:** `BreakdownResponse`
- **Business Rule:** Sum of items (including `Other`) exactly equals `total`.

#### `GET /api/v1/analytics/kpis`
- **Purpose:** Summary KPI card payload combining complaint volume, primary and legacy timely resolution rates, routing delay, and coverage dates.
- **Parameters:** Common query filters.
- **Response Schema:** `KPISummaryResponse`

---

### 2.4 Complaint Explorer & Export Endpoints

#### `GET /api/v1/complaints`
- **Purpose:** Paginated, filtered, and deterministically sorted complaint browsing (§13.2 #9).
- **Parameters:**
  - `q`: Search query matching exact `Complaint_ID` (digits only, $\le 12$ characters).
  - `sort` / `sort_by`: `date_submitted` (default), `complaint_id`, `category`, `sub_category`, `submitted_via`, `state`, `company_response`.
  - `order` / `sort_dir`: `desc` (default) or `asc`. Secondary tie-break strictly on `Complaint_ID` descending.
  - `page`: Page number (integer $\ge 1$, default 1).
  - `page_size`: Records per page (integer between 1 and 100, default 25).
  - Common query filters.
- **Response Schema:** `ComplaintListResponse`
```json
{
  "items": [
    {
      "complaint_id": 4848023,
      "date_submitted": "2021-10-24",
      "category": "Lending",
      "sub_category": "Real Estate Lending",
      "product": "Mortgage",
      "issue": "Applying for a mortgage or refinancing an existing mortgage",
      "submitted_via": "Referral",
      "state": "NY",
      "company_response": "Closed with explanation",
      "timely_response": "yes",
      "is_anomaly": false
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 62516,
  "total_pages": 2501
}
```

#### `GET /api/v1/complaints/{complaint_id}`
- **Purpose:** Full detail record for a single complaint (§13.2 #10).
- **Parameters:**
  - `complaint_id`: Positive integer CFPB identifier in URL path.
- **Response Schema:** `ComplaintDetailResponse`
- **Error Cases:** HTTP 404 `NOT_FOUND` if ID does not exist; HTTP 422 if non-numeric.

#### `GET /api/v1/complaints/export`
- **Purpose:** Capped streaming CSV export of filtered complaints (§13.2 #11).
- **Parameters:** Same filter and sort parameters as `/api/v1/complaints`.
- **Response:** `text/csv; charset=utf-8` stream with RFC 4180 quotation.
- **Headers:**
  - `Content-Disposition`: `attachment; filename="complaints_YYYYMMDD.csv"`
  - `X-Export-Truncated`: `"true"` if total matching records exceed `EXPORT_MAX_ROWS` (default 10,000), else `"false"`.
  - `X-Export-Row-Count`: Total exported data rows (e.g. `"10000"`).
- **Security:** Formula-injection guard prefixes `'` to any cell starting with `=`, `+`, `-`, `@`, `\t`, or `\r`.

---

### 2.5 Data Quality Center Endpoints

#### `GET /api/v1/quality/summary`
- **Purpose:** Overall composite data quality score, decomposed dimensions, anomaly distributions, model metadata, and mandatory audit caveats (§13.2 #12).
- **Parameters:** None.
- **Response Schema:** `QualitySummaryResponse`
```json
{
  "overall_quality_score": 98.7,
  "status": "HIGH QUALITY",
  "total_records": 62516,
  "dimensions": [
    {
      "id": "completeness",
      "label": "Completeness",
      "value": 99.6,
      "weight": 0.25,
      "definition": "Proportion of non-null attributes across mandatory complaint schema fields.",
      "note": "Lowered by 1,494 open ('In progress') cases with no timeliness value."
    },
    {
      "id": "validity",
      "label": "Validity",
      "value": 98.8,
      "weight": 0.20,
      "definition": "Conformance to domain ranges, enumerated categories, and resolved response values.",
      "note": "Timely response recorded as Yes or No for 61,022 of 62,516 complaints."
    },
    {
      "id": "consistency",
      "label": "Consistency",
      "value": 100.0,
      "weight": 0.20,
      "definition": "Chronological consistency between complaint submission date and CFPB receipt date.",
      "note": "CFPB routing logic verified: Date received >= Date submitted across all valid records."
    },
    {
      "id": "uniqueness",
      "label": "Uniqueness",
      "value": 100.0,
      "weight": 0.15,
      "definition": "Distinctness of primary complaint identifiers (Complaint_ID uniqueness).",
      "note": "Zero duplicate Complaint_IDs detected in Silver layer."
    },
    {
      "id": "ml_normality",
      "label": "ML Normality",
      "value": 95.0,
      "weight": 0.20,
      "definition": "Proportion of complaints exhibiting normal multivariate behavior via Isolation Forest.",
      "note": "Derived from Isolation Forest anomaly detection (nominal contamination=0.05)."
    }
  ],
  "anomalies": {
    "flagged": 3126,
    "rate_pct": 5.0,
    "in_progress_share_pct": 47.79,
    "by_category": [
      { "category": "Banking", "flagged": 1064, "total": 24814, "rate_pct": 4.29 },
      { "category": "Payments", "flagged": 967, "total": 19650, "rate_pct": 4.92 }
    ],
    "by_company_response": [
      { "company_response": "In progress", "flagged": 1494, "total": 1494, "rate_pct": 100.0 }
    ]
  },
  "model": {
    "available": true,
    "type": "IsolationForest",
    "contamination": 0.05,
    "n_estimators": 200,
    "features": [
      "Days_to_Respond",
      "is_timely",
      "Category_code",
      "Sub_Category_code",
      "Submitted_Via_code",
      "Company_Response_code"
    ],
    "mlflow_run_id": "local_snapshot_reproduction",
    "source": "run_metadata"
  },
  "timestamps": {
    "quality_analysis_at": "2026-10-19T10:31:18.434201+00:00",
    "report_object_refreshed_at": "2026-10-19T11:00:00Z"
  },
  "limitations": [
    "ML Normality is derived from the fixed contamination parameter (0.05) and is ~95.0% by construction, rather than an empirical distribution test.",
    "Completeness and Validity scores are mechanically depressed by open ('In progress') complaints, which cannot have a timeliness verdict until resolved.",
    "Isolation Forest anomaly detection uses label-encoded categorical variables and median-imputed routing delays; anomalies represent unusual feature combinations, not confirmed data errors.",
    "Anomalies are heavily concentrated in open cases (1,494 of 1,494 in-progress complaints flagged) and cases with extended CFPB routing delays."
  ],
  "warnings": []
}
```

#### `GET /api/v1/quality/anomalies`
- **Purpose:** Paginated anomaly records joined with Silver complaints and deterministic observations (§13.2 #13).
- **Parameters:**
  - `only_flagged`: Boolean (default `true`). If `false`, includes unflagged complaints.
  - `sort` / `sort_by`: `score` (default, lowest score first), `date`, `id`.
  - `order` / `sort_dir`: `asc` (default) or `desc`.
  - `page`: Page number ($\ge 1$, default 1).
  - `page_size`: Records per page ($1 \le \text{page\_size} \le 100$, default 25).
  - `category`: Repeatable filter by product category.
  - `sub_category`: Repeatable filter by sub-category.
  - `company_response`: Repeatable filter by company response.
- **Response Schema:** `AnomalyListResponse`
```json
{
  "items": [
    {
      "complaint_id": 1234567,
      "date_submitted": "2020-01-01",
      "category": "Credit Reporting",
      "sub_category": "Credit reporting",
      "product": "Credit reporting",
      "issue": "Incorrect information on your report",
      "submitted_via": "Web",
      "state": "CA",
      "company_response": "In progress",
      "timely_response": null,
      "days_submitted_to_received": 0,
      "anomaly_score": -0.123456,
      "is_anomaly": true,
      "annotations": {
        "open_case": true,
        "long_routing_delay": false,
        "timely_no": false
      },
      "annotations_note": "Observations, not model explanations"
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 3126,
  "total_pages": 126
}
```

---

### 2.6 AI Assistant Endpoints

#### `GET /api/v1/assistant/config`
- **Purpose:** Surfaces AI Assistant availability, operational mode (`llm` or `degraded`), limits, and curated suggested questions (§13.3 #14).
- **Parameters:** None.
- **Cache-Control:** `private, max-age=60`
- **Response Schema:** `AssistantConfigResponse`
```json
{
  "available": true,
  "mode": "llm",
  "suggested_questions": [
    {
      "id": "sq_overview",
      "text": "What is the total number of complaints and the timely response rate across the dataset?",
      "tool_hint": "get_dataset_overview"
    },
    {
      "id": "sq_top_category",
      "text": "Which financial product category received the highest volume of consumer complaints?",
      "tool_hint": "compare_categories"
    },
    {
      "id": "sq_trends",
      "text": "How did complaint volume trend year-over-year between 2018 and 2022?",
      "tool_hint": "get_trend"
    },
    {
      "id": "sq_channels",
      "text": "What are the most common submission channels consumers use to file complaints?",
      "tool_hint": "get_breakdown"
    },
    {
      "id": "sq_dq",
      "text": "What is the overall data quality composite score and what are its key limitations?",
      "tool_hint": "get_quality_summary"
    },
    {
      "id": "sq_timely_def",
      "text": "How is the primary timely response rate calculated and how does it differ from the legacy rate?",
      "tool_hint": "explain_metric"
    }
  ],
  "limits": {
    "max_question_chars": 500,
    "max_history_turns": 6,
    "daily_request_cap": 300,
    "max_output_tokens": 700
  }
}
```

#### `POST /api/v1/assistant/chat`
- **Purpose:** Answers user inquiries strictly grounded in backend analytical tools (T1–T8) with 100% numerical fact verification and deterministic fallback (§13.3 #15, §14).
- **Cache-Control:** `no-store`
- **Request Body:** `AssistantChatRequest`
```json
{
  "question": "Which category received the highest volume of complaints?",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "How can I help you analyze financial complaints today?"}
  ],
  "context_filters": {
    "date_from": "2020-01-01",
    "date_to": "2022-12-31"
  },
  "suggested_question_id": null
}
```
- **Response Schema:** `AssistantChatResponse`
```json
{
  "status": "answered",
  "answer_markdown": "Across categories, Banking accounts for the largest share with 24,814 complaints (39.69% of total) and a timely response rate of 96.4%.",
  "data_blocks": [
    {
      "type": "table",
      "title": "Category Comparison (category)",
      "columns": ["Name", "Total Complaints", "Share", "Timely Rate"],
      "rows": [
        ["Banking", 24814, "39.69%", "96.4%"],
        ["Payments", 19650, "31.43%", "95.73%"]
      ],
      "source_tool": "compare_categories",
      "dataset_as_of": "2023-08-28"
    }
  ],
  "evidence": [
    {
      "tool": "compare_categories",
      "arguments": {"group_by": "category", "sort": "total"},
      "metric_ids": ["M-01", "M-03", "M-04", "M-10"],
      "dataset_origin": "local_snapshot",
      "pipeline_refreshed_at": "2026-10-19T10:31:18.434201+00:00"
    }
  ],
  "limitations": [
    "Dataset contains 62,516 complaints from May 2017 to August 2023 across 5 financial categories.",
    "Specific company names, consumer narratives, and root-cause explanations are not present in this dataset.",
    "Years 2017 and 2023 are partial periods; annual YoY comparisons are computed only between 2018 and 2022.",
    "Days submitted to received measures CFPB routing lag, not company response time.",
    "ML Normality score is derived from the fixed 5% contamination parameter of the Isolation Forest model."
  ],
  "grounding": {
    "checked": true,
    "ungrounded_numbers": 0,
    "fallback_used": false
  },
  "request_id": "403d6c53-1c3a-4a2e-8367-e9a93c7d6b38"
}
```
- **Operational Status Values:**
  - `answered`: User inquiry answered through validated tools and passed strict numeric grounding.
  - `unsupported`: Question exceeds dataset boundaries (specific company names, causation, forecasting, legal advice).
  - `degraded`: Upstream LLM unavailable/disabled; served via deterministic verified fallback templates.


