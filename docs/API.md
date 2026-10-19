# Backend API Specification

**Document:** `docs/API.md`  
**Phase:** Phase 3 — Core Analytics APIs (Draft Contract)  
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
