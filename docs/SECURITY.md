# Security Architecture and Audit Report

**Document:** `docs/SECURITY.md`  
**Phase:** Phase 6 — Backend Integration, Security and API Freeze  
**Date:** 2026-10-19  
**Status:** Complete & Verified  

---

## 1. Security Architecture & Threat Boundaries

The Finance Complaints Medallion platform is designed around a multi-layered defence-in-depth model that protects analytical data, LLM endpoints, and server resources:

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                         │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP (Same-Origin)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          Next.js BFF Server Proxy (Phase 7)                 │
│  - Restricts routes to explicit allow-list                  │
│  - Injects X-Internal-Key (never exposed to browser)         │
│  - Forwards client IP via X-Forwarded-For                   │
│  - Strips hop-by-hop headers and credentials                │
└──────────────────────────────┬──────────────────────────────┘
                               │ Internal Server-to-Server
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (Phase 2–6)                 │
│  Layer 1: RequestIDMiddleware (Request Tracing)             │
│  Layer 2: CORSMiddleware (Explicit Origins, No Credentials) │
│  Layer 3: RequestBodyLimitMiddleware (Max 64 KB)            │
│  Layer 4: SecurityHeadersMiddleware (nosniff, DENY, etc.)   │
│  Layer 5: SlowAPIMiddleware (Rate Limiting Tiers)           │
│  Layer 6: verify_internal_api_key (secrets.compare_digest)  │
│  Layer 7: Exception Handlers (Sanitized Envelopes)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Enforced Security Controls

### 2.1 Internal API Key Authentication
- **Mechanism:** Header `X-Internal-Key` validated via constant-time comparison (`secrets.compare_digest`) to prevent timing attacks.
- **Enforcement:** Mandatory when `APP_ENV=production` or whenever `INTERNAL_API_KEY` is configured in the environment.
- **Exemptions:** Unauthenticated liveness probes (`/health/live`) and local development when `INTERNAL_API_KEY` is left blank.
- **Failure Mode:** Returns HTTP 401 Unauthorized with standardized error envelope (`UNAUTHORIZED`).

### 2.2 CORS Policy
- Configured via `CORS_ALLOW_ORIGINS` settings (defaults to `http://localhost:3000`).
- **No Credentials:** `allow_credentials=False` to prevent cross-origin session hijacking.
- **Method Whitelist:** Strictly `["GET", "POST", "OPTIONS"]`.
- **Header Whitelist:** Restricted to `["Content-Type", "X-Request-ID", "X-Internal-Key"]`.
- **Production Guard:** Wildcard (`*`) origins in `CORS_ALLOW_ORIGINS` are rejected at startup.

### 2.3 Request Body Limits
- Enforced via `RequestBodyLimitMiddleware` using `MAX_REQUEST_BYTES` (default: 65,536 bytes / 64 KB).
- Evaluates both `Content-Length` header on arrival and streaming chunks.
- Rejection returns HTTP 413 `PAYLOAD_TOO_LARGE` without reading excessive memory.

### 2.4 Rate Limiting Tiers
Rate limiting is managed in-process via `slowapi` (`limits` token bucket), tracking client IPs resolved from `X-Forwarded-For` or `request.client.host`:
- **Default Tier:** 120 requests/minute on standard endpoints (`/api/v1/meta/*`, `/api/v1/dashboard/*`, `/api/v1/analytics/*`, `/api/v1/quality/*`, `/api/v1/complaints`).
- **Export Tier:** 10 requests/hour on `/api/v1/complaints/export`.
- **AI Assistant Tier:** 10 requests/minute on `/api/v1/assistant/chat`.
- **Health Exemption:** `/health/live` and `/health/ready` are decorated with `@limiter.exempt`.
- **Headers:** Rate-limited responses return HTTP 429 with `Retry-After` header and code `RATE_LIMITED`.

### 2.5 Security Headers & Cache Controls
Every response is injected with protective headers:
- `X-Content-Type-Options: nosniff` (prevents MIME type sniffing)
- `X-Frame-Options: DENY` (prevents clickjacking)
- `Referrer-Policy: strict-origin-when-cross-origin` (prevents referrer leakage)
- `Cache-Control`:
  - AI Assistant (`/api/v1/assistant/*`): `no-store, no-cache, must-revalidate`
  - Analytics & Dashboard: `private, max-age=60`
  - Complaints Explorer: `no-cache`

### 2.6 Error Sanitization
All exceptions pass through custom handlers in `app/core/errors.py`:
- No raw exception strings (`str(exc)`), stack traces, server paths (`C:\`, `D:\`, `/home/`), or database connection strings are ever leaked to the client.
- Unhandled 500 exceptions return: `"An unexpected internal server error occurred. Please quote the request ID."`

### 2.7 Production Startup Safeguards
Per §12.4, the backend refuses to start in `APP_ENV=production` if:
1. Wildcard `*` exists in `CORS_ALLOW_ORIGINS`.
2. `INTERNAL_API_KEY` is empty or shorter than 16 characters.
3. `AZURE_AUTH_MODE` is set to `connection_string` (managed identity required).
4. `LOG_AI_PROMPTS` is `True`.
5. `DATA_MODE` is set to `fixture`.

---

## 3. Security Audit & Scan Results

### 3.1 Secret Scanning (`scan_secrets.py` & `.gitleaks.toml`)
- **Target:** Full git commit history (`git log -p --full-history`) and working tree.
- **Configuration:** `.gitleaks.toml` with regex detectors for Azure storage connection strings, OpenAI API keys, RSA/SSH private keys, and high-entropy secrets.
- **Execution:** Executed `python backend/scripts/scan_secrets.py`.
- **Result:** **0 secrets found in git history.**
- **Evidence:**
  ```text
  SUCCESS: 0 secrets found in git history.
  ```

### 3.2 Dependency Vulnerability Audit (`pip-audit`)
- **Target:** Python production dependencies in `backend/requirements.txt`.
- **Database:** Open Source Vulnerabilities (OSV) database and PyPI Advisory Database.
- **Execution:** Executed `python -m pip_audit -r backend/requirements.txt`.
- **Result:** **No known vulnerabilities found.**
- **Evidence:**
  ```text
  No known vulnerabilities found
  ```

### 3.3 Security Test Suite Verification
- **Test File:** `backend/tests/api/test_security.py`
- **Result:** 8 passed in 13.32s.
- **Verified Scenarios:**
  - `test_internal_api_key_when_configured`: Missing (401), invalid (401), valid (200), `/health/live` exempt (200).
  - `test_internal_api_key_unconfigured_in_local`: Local dev without key passes (200).
  - `test_cors_preflight_allowed_and_denied_origin`: Allowed origin echoed without credentials, denied origin rejected.
  - `test_request_body_size_limit_rejection`: Payload > 1024 bytes rejected with 413 `PAYLOAD_TOO_LARGE`.
  - `test_security_headers_injected`: `nosniff`, `DENY`, `strict-origin`, and `Cache-Control` present.
  - `test_rate_limiter_trips_and_returns_retry_after`: 3rd export call trips limit -> 429 `RATE_LIMITED` with `Retry-After: 60`.
  - `test_production_safeguards_reject_unsafe_values`: Rejects wildcard CORS, short key, connection string, prompt logging, and fixture mode.
  - `test_error_responses_contain_no_filesystem_paths`: Error bodies contain zero file paths or tracebacks.
