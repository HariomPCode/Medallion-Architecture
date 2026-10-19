# System Architecture Document

**Document:** `docs/ARCHITECTURE.md`  
**Phase:** Phase 2 — Backend Foundation, Data Access and Fixtures  
**Version:** 1.0.0  
**Last Updated:** 2026-10-19  

---

## 1. Architectural Overview

The **Finance Complaints Medallion Platform** is structured as a cloud-native, modular analytics system designed to expose governed CFPB financial complaint data through deterministic metrics and a grounded AI assistant.

```
       ADLS Gen2 (Storage)                     FastAPI Backend                     Next.js Frontend
┌─────────────────────────────────┐      ┌─────────────────────────────┐      ┌─────────────────────────┐
│ silver/ConsumerComplaints_...   │ ───▶ │ SnapshotManager (In-Memory) │ ───▶ │ BFF Proxy Route Handlers│
│ gold/complaints_by_category_... │      │  - Dynamic Filtering        │      │  (holds INTERNAL_KEY)   │
│ gold/complaints_trend_...       │      │  - Deterministic Aggregates │      └───────────┬─────────────┘
│ gold/complaints_anomaly_...     │      │  - Grounded AI Orchestrator │                  │
│ gold/data_quality_report_...    │      └─────────────────────────────┘                  ▼
└─────────────────────────────────┘                                            Browser Dashboard (UI)
```

---

## 2. Key Architectural Decisions (From DECISIONS.md)

1. **Monorepo Layout (D-02):** Backend, frontend, documentation, scripts, and CI workflows reside in a single repository. Existing Databricks notebooks and Bronze CSV datasets stay untouched at repository root.
2. **In-Memory Analytical Engine (D-03, D-05):** The dataset (62,516 rows) occupies ~15–25 MB in memory. All multi-dimensional filtering and grouping are computed dynamically in pandas from the enriched Silver table. No relational database (PostgreSQL) or cache service (Redis) is needed.
3. **Medallion Data Ingestion via CSV (D-04):** The Databricks pipeline exports cleaned Silver and Gold summaries to ADLS Gen2 as CSVs. The backend ingests these blobs over HTTPS without requiring active Spark or Databricks compute clusters at query time.
4. **BFF Security Proxy (D-01, D-11):** Browsers never communicate with the backend directly. Next.js server-side route handlers proxy all requests and inject a shared `INTERNAL_API_KEY`.
5. **Pluggable Cloud Data Sources:** The data boundary is strictly abstracted behind the `DataSource` protocol. The platform can run in `fixture` mode (offline ~40 rows), `local_snapshot` mode (reproduced 62k rows), or `azure` mode (live ADLS Gen2).

---

## 3. Backend Module Hierarchy

```
backend/
├── app/
│   ├── main.py              # Application factory, CORS, request middleware, lifespan
│   ├── core/
│   │   ├── config.py        # Pydantic Settings with strict production safeguards
│   │   ├── logging.py       # JSON/console formatters, request-ID tracking, secret redaction filter
│   │   └── errors.py        # Authoritative error envelope, sanitized exception handlers
│   ├── data/
│   │   ├── contracts.py     # Schema contracts, column requirements, allowed null tokens
│   │   ├── loader.py        # UTF-8 BOM parser, trimming, date parsing, routing lag, joins
│   │   ├── sources.py       # DataSource protocol, LocalSource, AzureBlobSource
│   │   └── snapshot.py      # Immutable Snapshot, SnapshotManager, atomic swap, last-known-good refresh
│   └── api/
│       └── health.py        # GET /health/live, GET /health/ready
├── scripts/
│   ├── build_local_snapshot.py # Reproduces pipeline Silver/Gold tables offline
│   ├── reconcile_with_gold.py  # Validates local data against Appendix B targets
│   └── check_azure_access.py   # Probes ADLS Gen2 without printing secrets
└── tests/
    ├── fixtures/tiny/       # Hand-verified ~40-row test dataset + EXPECTED.md
    ├── unit/                # Unit test suite (config, logging, errors, loader, snapshot, Azure)
    └── api/                 # API endpoint tests (health probes)
```

---

## 4. Data Lifecycle and Snapshot Management

### Ingestion & Validation Flow
1. **Fetch:** `DataSource.fetch(blob_name)` downloads raw bytes and retrieves HTTP ETag / modified timestamps. Enforces `MAX_BLOB_BYTES` (100 MB ceiling).
2. **Normalize:** `parse_csv_bytes` strips Byte Order Marks (`utf-8-sig`), trims whitespace, and maps `{"", "nan", "NaN", "None", "null", "NULL"}` to `None`.
3. **Validate:** Enforces column presence per contract. Deduplicates by `Complaint_ID`. Validates date formats (fails if unparseable dates exceed 1.0%).
4. **Enrich:** Computes CFPB routing lag (`days_submitted_to_received = Date_received - Date_submitted`). Joins `Product` against `Product_Category_Reference`. Unmapped products are flagged as `"Unmapped"`.
5. **Atomic Swap:** A new immutable `Snapshot` instance is built completely in isolation. Once validated, `SnapshotManager` acquires an asynchronous lock and swaps the reference instantaneously.

### Last-Known-Good Failure Semantics
During recurring refresh polls (`DATA_REFRESH_CHECK_SECONDS`), if an ADLS blob is corrupted, in mid-write, or inaccessible:
- The existing valid snapshot is **retained in memory**.
- Manager status transitions from `fresh` to `stale`.
- A warning banner is displayed on the frontend via `/health/ready`.
- No half-built or invalid snapshot is ever exposed to incoming requests.

---

## 5. Security Architecture

- **Zero Secret Commits:** Sensitive keys (`INTERNAL_API_KEY`, `AZURE_STORAGE_CONNECTION_STRING`, `LLM_API_KEY`) are read exclusively from environment variables or Key Vault.
- **Log Redaction Filter:** All log output passes through `RedactionFilter`, which sanitizes substrings matching `key|secret|token|connection|password|sig`.
- **Production Safeguards:**
  - Wildcard CORS (`*`) is rejected at startup when `APP_ENV=production`.
  - `INTERNAL_API_KEY` must be at least 16 characters in production.
  - Connection string auth is disallowed in production (mandating Managed Identity).
  - Prompt logging (`LOG_AI_PROMPTS=true`) is blocked in production.
  - Test `fixture` data mode is blocked in production.
