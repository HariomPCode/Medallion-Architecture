# System Architecture Document

**Document:** `docs/ARCHITECTURE.md`  
**Phase:** Phase 6 — Backend Hardening & API Freeze  
**Version:** 1.1.0  
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
│   ├── main.py                 # Application factory, middleware stack, CORS, lifespan
│   ├── core/
│   │   ├── config.py           # Pydantic Settings with strict production safeguards
│   │   ├── logging.py          # Structured JSON formatters, request ID tracking, redaction filter
│   │   ├── errors.py           # Authoritative sanitized error envelope & handlers
│   │   ├── security.py         # Constant-time API key auth, body size limit, security headers
│   │   └── ratelimit.py        # slowapi Limiter with IP resolution and tier definitions
│   ├── data/
│   │   ├── contracts.py        # Schema contracts, column validation, null tokens
│   │   ├── loader.py           # UTF-8 BOM parser, trimming, date parsing, routing lag, joins
│   │   ├── sources.py          # DataSource protocol, LocalSource, AzureBlobSource
│   │   └── snapshot.py         # Immutable Snapshot, SnapshotManager, atomic swap, last-known-good
│   ├── domain/
│   │   ├── metrics.py          # Metric specifications M-01 to M-15 with exact formulas
│   │   ├── filters.py          # ComplaintFilters model, dimension validation, vectorised filtering
│   │   ├── aggregates.py       # Deterministic KPIs, category comparisons, trends, breakdowns
│   │   ├── complaints.py       # Paged complaint listing, detail projection, CSV export
│   │   └── quality.py          # 5 quality dimensions, anomaly scores, and observational flags
│   ├── schemas/
│   │   ├── common.py           # Error envelopes, filter params, shared models
│   │   ├── analytics.py        # Pydantic models for summary, category, trends, breakdown, KPIs
│   │   ├── complaints.py       # Complaint list, detail, and export schemas
│   │   ├── quality.py          # Quality summary and anomaly list schemas
│   │   └── assistant.py        # AI chat request, response, grounding metadata, data blocks
│   ├── assistant/
│   │   ├── budget.py           # In-memory daily request budget tracker with midnight rollover
│   │   ├── llm.py              # LLMClient protocol, DisabledLLMClient, FakeLLMClient, AzureOpenAIClient
│   │   ├── tools.py            # Read-only analytical tools T1–T8 with standardized envelopes
│   │   ├── prompts.py          # System prompt with regulatory guidelines & dynamic OpenAI tool schemas
│   │   ├── grounding.py        # Numeric claim verification, ungrounded rejection, fallback renderer
│   │   └── orchestrator.py     # Multi-turn tool calling loop, budget enforcement, grounding check
│   └── api/
│       ├── deps.py             # FastAPI dependencies (snapshot manager, API key auth)
│       ├── health.py           # GET /health/live, GET /health/ready
│       ├── meta.py             # GET /api/v1/meta/dataset, GET /api/v1/meta/filters
│       ├── dashboard.py        # GET /api/v1/dashboard/summary
│       ├── analytics.py        # GET /api/v1/analytics/{by-category, trends, breakdown, kpis}
│       ├── complaints.py       # GET /api/v1/complaints, GET /api/v1/complaints/{id}, GET .../export
│       ├── quality.py          # GET /api/v1/quality/summary, GET /api/v1/quality/anomalies
│       └── assistant.py        # GET /api/v1/assistant/config, POST /api/v1/assistant/chat
├── scripts/
│   ├── build_local_snapshot.py # Reproduces pipeline Silver/Gold tables offline
│   ├── reconcile_with_gold.py  # Validates local data against Appendix B targets
│   ├── check_azure_access.py   # Probes ADLS Gen2 without printing secrets
│   ├── export_openapi.py       # Generates docs/openapi.json from FastAPI app
│   ├── run_ai_eval.py          # Executes 26-question AI evaluation suite
│   ├── loadcheck.py            # 20 concurrent clients x 200 requests load verification
│   └── scan_secrets.py         # Full git history secret scanning against .gitleaks.toml
└── tests/
    ├── fixtures/tiny/          # Hand-verified ~40-row test dataset + EXPECTED.md
    ├── unit/                   # Unit test suite (domain, config, logging, loader, snapshot)
    ├── api/                    # Endpoint functional tests & security tests
    ├── assistant/              # Assistant budget, llm, tools, prompts, grounding, safety tests
    └── integration/            # Cross-endpoint consistency, reliability, contract tests
```

---

## 4. Security & Hardening Architecture

1. **Authentication:**
   - Enforced by `verify_internal_api_key` using constant-time comparison (`secrets.compare_digest`).
   - Exempt routes: `/health/live`, `/health/ready`, `/docs`, `/openapi.json`, and preflight `OPTIONS`.
   - Returns sanitized `401 UNAUTHORIZED` on missing or incorrect credentials.

2. **Rate Limiting:**
   - Powered by `slowapi` utilizing client IP address resolution.
   - Three rate tiers:
     - **Default:** 120 req/min for general API routes.
     - **Export:** 10 req/hr for `/api/v1/complaints/export`.
     - **AI Assistant:** 10 req/min for `/api/v1/assistant/chat`.
   - Exceeded limits yield `429 RATE_LIMITED` with standard `Retry-After` header.

3. **Request Body Ceiling:**
   - Enforced by `RequestBodyLimitMiddleware` inspecting `Content-Length` and streaming chunks.
   - Rejects any payload > 64 KB (65,536 bytes) with `413 PAYLOAD_TOO_LARGE`.

4. **Security Headers:**
   - `SecurityHeadersMiddleware` injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Cache-Control: no-store, max-age=0` (or `no-cache` on health).

5. **CORS Hardening:**
   - Explicit allowed origins without credentials (`allow_credentials=False`).
   - Restricts HTTP methods to `GET`, `POST`, and `OPTIONS`.
   - In production mode, wildcard origins (`*`) are strictly forbidden and prevent application startup.

6. **Contract Snapshot Freeze:**
   - The OpenAPI 3.1 specification is committed to `docs/openapi.json`.
   - `backend/tests/integration/test_contract.py` runs in CI, asserting that `app.openapi()` matches `docs/openapi.json` character-for-character.

---

## 5. Grounded AI Assistant Pipeline

```
  User Prompt ──▶ Budget Check (≤ 300/day)
                        │
                        ▼
               OpenAI Tool Calling (T1–T8)
                        │
                        ▼
          Read-Only Domain Metric Engines
                        │
                        ▼
             Raw Model Synthesis Text
                        │
                        ▼
             Grounding Verification
             ┌──────────┴──────────┐
          Pass                   Fail
             │                     │
             ▼                     ▼
      Verified Response    Deterministic Fallback Template
             │                     │
             └──────────┬──────────┘
                        ▼
           Response Envelope + Data Blocks
```

- **Read-Only Tools:** Assistant tools (T1–T8) call directly into existing domain analytics and complaint search services. The model cannot execute arbitrary code or SQL.
- **Strict Grounding:** `verify_grounding` extracts all numeric tokens and requires every numeral to match tool evidence within $\pm 0.05$ tolerance (allowing standard years, small ordinals, and constants).
- **Deterministic Fallback:** If any hallucinated or ungrounded number is detected, the narrative is replaced with deterministic templates populated directly from tool results. The response is flagged with `"fallback_used": true`.

