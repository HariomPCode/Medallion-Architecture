# Architecture and Technical Decision Register

**Document:** `docs/DECISIONS.md`  
**Phase:** Phase 1 — Repository Bootstrap, Baseline Verification and Decisions  
**Date:** 2026-10-19  
**Status:** Approved Defaults Recorded

---

## 1. Decision Register (D-01 through D-16)

The following register captures foundational architectural and technical decisions approved for the Finance Complaints Medallion platform. Unless explicitly overridden by the project team, each decision is marked as `ACCEPTED-DEFAULT`.

| ID | Decision | Status | Rationale | Implications |
| :--- | :--- | :--- | :--- | :--- |
| **D-01** | **Target Audience & Auth:** Platform audience is evaluator/team; no end-user authentication in v1. | `ACCEPTED-DEFAULT` | Public CFPB-derived research data. Eliminates user auth complexity while focusing on analytical depth and AI capabilities. | No user login tables; security boundary is handled via Next.js BFF proxy holding an internal server-to-server API key. |
| **D-02** | **Monorepo Structure:** Keep backend, frontend, docs, scripts, and CI workflows in a single repository; preserve all existing files at repo root. | `ACCEPTED-DEFAULT` | Single repository for submission, evaluation, and paired frontend/backend evolution. | Existing datasets, notebooks, and PBIX remain in root; new code lives in `backend/`, `frontend/`, `docs/`, `scripts/`. |
| **D-03** | **Analytical Computation Source:** Backend computes analytics dynamically from Silver CSV + Product Reference in pandas; Gold CSVs used for reconciliation tests and anomaly/DQ outputs. | `ACCEPTED-DEFAULT` | Pipeline Gold tables are pre-aggregated (Category × Sub-Category and Year × Category) and lack dimensions like State, Channel, Month, and Issue. Dynamic filtering requires Silver. | Consistent multi-dimensional filtering across all views; Gold aggregates serve as automated regression tests. |
| **D-04** | **Data Format in ADLS:** Consume CSV exports from ADLS Gen2, rather than querying Delta tables or Databricks SQL directly. | `ACCEPTED-DEFAULT` | Databricks pipeline already exports CSVs to `silver` and `gold` containers. Eliminates dependency on active Databricks compute clusters at runtime. | Zero compute costs while querying; backend loads and caches datasets in memory. |
| **D-05** | **Zero Database / In-Memory Storage:** No relational application database (PostgreSQL) or cache service (Redis). Hold the 62,516 records in memory. | `ACCEPTED-DEFAULT` | 62,516 records occupy ~15–25 MB in memory. Pandas provides sub-10ms response times for aggregations and filtering. | Architecture is stateless, lightweight, easily reproducible locally, and inexpensive to host. |
| **D-06** | **Dual Timely-Response Metrics:** Establish `M-03` (`timely_response_rate`, denominator = resolved cases) as primary, while preserving `M-04` (`timely_response_rate_all_cases`, denominator = all cases) for legacy reconciliation. | `ACCEPTED-DEFAULT` | 1,494 open cases cannot be judged untimely before resolution. Dividing by all cases distorts actual compliance. | Both metrics are computed and exposed; UI displays the primary rate with a clear tooltip and reconciliation toggle. |
| **D-07** | **Minimal Pipeline Intrusion:** Consume existing anomaly and DQ notebook outputs as produced; pipeline code modified only via documented, optional human-applied patches. | `ACCEPTED-DEFAULT` | Existing pipeline works; notebooks should remain stable artifacts. | Avoids breaking Databricks workspace configurations or schema expectations. |
| **D-08** | **Transparent DQ Scoring:** Display the notebook's composite DQ score (98.7%) with its decomposed sub-scores and mandatory methodology/limitation notes. | `ACCEPTED-DEFAULT` | The "ML Normality" component equals `1 - contamination = 95.0%` by design. Honesty in analytics requires disclosing this limitation. | Users see the original 98.7% composite score, but also understand how each dimension was derived. |
| **D-09** | **Pluggable LLM Integration:** Interface against Azure AI Foundry / Azure OpenAI via an abstract `LLMClient`, with `FakeLLMClient` for offline testing and a graceful degraded mode. | `ACCEPTED-DEFAULT` | Development and CI must never depend on live cloud credentials or API quota. | Full local testability without cloud access; platform works even when LLM keys are absent. |
| **D-10** | **Stateless AI Assistant:** Client transmits the last ≤ 6 dialogue turns with each prompt; no server-side conversation database; never log prompts. | `ACCEPTED-DEFAULT` | Preserves data privacy and eliminates database infrastructure requirements. | Simplifies backend; assistant context is ephemeral and controlled by the client. |
| **D-11** | **Next.js BFF Security Proxy:** Frontend server-side route handlers proxy all requests to the FastAPI backend, injecting the `INTERNAL_API_KEY`. | `ACCEPTED-DEFAULT` | Browser clients never possess internal API keys or direct backend endpoints; restricts public attack surface. | Backend CORS allows only the Next.js server origin in production. |
| **D-12** | **No Docker in v1:** Run Python backend directly on Azure App Service and Next.js frontend directly on Vercel. | `ACCEPTED-DEFAULT` | Python 3.12 runtime on App Service and Node on Vercel provide excellent native deployment with zero container overhead. | Simplified CI/CD pipelines; Docker can be introduced later if team demands it. |
| **D-13** | **Hosting Architecture:** Azure App Service (Linux, Python 3.12, B1 tier) for Backend; Vercel for Frontend. | `ACCEPTED-DEFAULT` | Backend colocated with ADLS storage in Azure; Vercel provides optimal Next.js SSR and edge delivery. | Free/low-cost tiers; keyless access to ADLS via system-assigned managed identity. |
| **D-14** | **Controlled Branching & Progression:** Phase-by-phase development; branch `phase/NN-slug` or develop cleanly on `main` per team git policy; pull requests and exit gates before advancing. | `ACCEPTED-DEFAULT` | Prevents scope creep and ensures each phase satisfies acceptance criteria before downstream work commences. | Strict phase boundaries maintained; Phase 1 executed in isolation. |
| **D-15** | **Light Theme in v1:** Frontend built strictly in a clean, professional light theme. | `ACCEPTED-DEFAULT` | Scoping decision; ensures high visual polish and contrast on data visualisations before considering themes. | Dark theme deferred to future enhancement. |
| **D-16** | **Slide-out Explorer Drawer:** Complaint details displayed in a slide-out drawer (`?selected=<id>`) rather than navigating to a separate page. | `ACCEPTED-DEFAULT` | Retains table filtering and pagination context while examining individual complaint records. | Fast, intuitive user experience when triaging multiple complaints. |

---

## 2. Metric Definition Rules & Principles

1. **Routing Delay (`M-09`):**  
   `Date_received − Date_submitted` represents the CFPB routing delay, **not** company response time. Confirmed by `ConsumerComplaints_DataDictionary.csv`. It will be labelled as "Routing Lag (CFPB to Company)".
2. **Partial Year Flagging (`M-07`, `M-08`):**  
   Year 2017 (starts 2017-05-01) and Year 2023 (ends 2023-08-28) represent partial years. Year-over-Year calculations are strictly limited to complete calendar years (2018 through 2022).
3. **No Unverified Data:**  
   The dataset does not contain company names, financial institution identifiers, or free-text consumer narratives. The assistant and dashboard will explicitly state these boundaries.

---

## 3. Open Questions Requiring User / Team Feedback

The following questions have safe defaults established in this plan. If the team prefers an alternate approach, a decision should be recorded before entering the affected phase:

| # | Question | Current Default in Use | Phase Needed | Action if Overridden |
| :--- | :--- | :--- | :--- | :--- |
| **Q-1** | Are the storage account name (`financecomplaintssa`) and container names (`bronze`, `silver`, `gold`) confirmed in Azure? | Use `financecomplaintssa` as configurable default via environment variables. | Phase 2 (Day 5) | Update `.env` / App Service configuration with actual names. |
| **Q-2** | Does the team have subscription permissions to grant `Storage Blob Data Reader` RBAC to an App Service Managed Identity? | Default to Managed Identity; fall back to Storage Connection String or SAS token for local/dev use. | Phase 11 | Use connection string if RBAC cannot be assigned. |
| **Q-3** | Is an Azure AI Foundry or Azure OpenAI resource deployed and available for the AI assistant? | Use `FakeLLMClient` and degraded mode for testing; plug in live Azure OpenAI credentials when available. | Phase 5 & Phase 10 | Configure endpoint, deployment name, and API key in backend. |
| **Q-4** | Is Vercel acceptable for hosting the Next.js frontend, or does the team mandate deploying both frontend and backend to Azure? | Deploy frontend to Vercel (recommended); fallback option is a second Azure App Service (Node runtime). | Phase 7 & Phase 11 | Update deployment workflow to Azure App Service if Vercel is disallowed. |
| **Q-5** | Should development proceed with dedicated phase branches (`phase/01-bootstrap`, etc.) or directly on the current branch (`main`)? | Follow user's specific instruction to avoid changing branches automatically; use `main` or requested branch. | Immediate | Confirm git branching strategy with repository owner. |
