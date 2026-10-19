# AI Assistant Evaluation Report

**Document:** `docs/AI_EVAL.md`  
**Phase:** Phase 5 (Grounded AI Assistant Backend)  
**Last Updated:** 2026-10-19  
**Status:** Evaluation Suite Verified (100% Pass in Offline/Deterministic Mode)  
**External Verification Status:** `BLOCKED_EXTERNAL: live-llm-verification` (Azure AI Foundry / OpenAI quota unconfigured locally)

---

## 1. Executive Summary

This report documents the design, execution, and verification results of the **AI Assistant Evaluation Suite** per §1246 and §1258 of [FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/docs/FINANCE_COMPLAINTS_DEVELOPMENT_PLAN.md).

The evaluation tests the assistant's ability to:
1. Accurately select and invoke the 8 read-only analytical tools (T1–T8).
2. Ground all numerical assertions, percentages, dates, and category claims strictly in verified tool results.
3. Automatically refuse unsupported questions (such as inquiries regarding specific company names, causation narratives, forecasting, or legal advice) without fabricating facts.
4. Safely fallback to deterministic templated responses whenever an LLM generates ungrounded or contradictory numbers.

---

## 2. Evaluation Methodology & Test Matrix

The evaluation suite is defined declaratively in [`backend/tests/assistant/eval_questions.yaml`](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/backend/tests/assistant/eval_questions.yaml) and executed via the CLI runner [`backend/scripts/run_ai_eval.py`](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/backend/scripts/run_ai_eval.py).

The suite comprises **26 curated questions** across 6 distinct evaluation groups:

| Group ID | Topic | Tool Expected | Question Count | Key Authoritative Numbers Checked |
| :--- | :--- | :---: | :---: | :--- |
| **G1** | Numeric Overview & KPIs | T1 (`get_dataset_overview`) | 5 | 62,516 complaints, 96.06% timely rate, 61,022 denominator, 1,494 open cases |
| **G2** | Category Comparisons | T2 (`compare_categories`) | 6 | Banking 24,814 (39.69%), Payments 19,650 (31.43%), Collections 2,736, Lending sub-categories |
| **G3** | Trends & YoY Growth | T3 (`get_trend`) | 5 | Annual counts 2018–2022, YoY growth 2020 (+26.39%) and 2021 (+24.68%), partial years (2017, 2023) |
| **G4** | Quality & Anomalies | T6 / T7 (`get_quality_summary`, `list_anomalies`) | 3 | Composite score 98.7, 3,120 flagged anomalies (4.99%), open cases share (~48%) |
| **G5** | Metric Explanations | T8 (`explain_metric`) | 3 | M-03 (61,022 denominator), M-04 (62,516 legacy denominator), M-09 (routing delay) |
| **G6** | Unsupported Queries | None (Refusal via `UNSUPPORTED:`) | 4 | Wells Fargo / Bank of America, causation narratives, forecasting, legal advice |

---

## 3. Grounding Verification & Zero-Hallucination Guardrails

The assistant enforces a strict two-stage grounding check ([`backend/app/assistant/grounding.py`](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/backend/app/assistant/grounding.py)):

1. **Numeral Extraction:** Every integer, float, percentage, and growth delta is extracted from the generated narrative using regex tokenization.
2. **Authoritative Matching:** Extracted numbers are validated against the set of numbers harvested from executed tool output dictionaries with a tolerance of $\pm 0.05$ (to allow for half-up rounding).
3. **Small Ordinals & Years:** Small ordinals ($\le 10$) and dataset coverage years (2017–2026) are permitted as structural discourse markers.
4. **Deterministic Fallback Renderer:** If an LLM response contains even a single ungrounded number or fabricated claim, the narrative is completely rejected and replaced with the deterministic template renderer (`render_fallback`).

---

## 4. Benchmark Execution Results

### A. Offline / Scripted Evaluation (CI Mode)
Command:
```powershell
backend\.venv\Scripts\python backend/scripts/run_ai_eval.py
```

Results:
```
===========================================================================
AI ASSISTANT EVALUATION SUMMARY
===========================================================================
Total Questions Evaluated  : 26
Overall Passed             : 26/26 (100.0%)
Tool Selection Accuracy    : 26/26 (100.0%)
Numeric Grounding Rate     : 26/26 (100.0%) [TARGET: 100%]
Total Evaluation Duration  : 0.16s
Total Prompt Tokens        : 2,540
Total Completion Tokens    : 815
===========================================================================
ALL EVALUATION CRITERIA PASSED: 100% TOOL ROUTING AND 100% GROUNDED NUMBERS
```

### B. Live LLM Evaluation Status
When executed with `--live`:
```powershell
backend\.venv\Scripts\python backend/scripts/run_ai_eval.py --live
```

Result:
```
[BLOCKED_EXTERNAL: live-llm-verification]
Live evaluation requires LLM_ENDPOINT and LLM_API_KEY or Entra ID credentials.
To run live verification:
  1. Set LLM_PROVIDER=azure_openai
  2. Set LLM_ENDPOINT=https://<your-instance>.openai.azure.com/
  3. Set LLM_DEPLOYMENT=<deployment-name>
  4. Set LLM_API_KEY=<key>
  5. Re-run: python scripts/run_ai_eval.py --live
```
Recorded as `BLOCKED_EXTERNAL: live-llm-verification` in `docs/DEVELOPMENT_STATUS.md`.

---

## 5. Failure Mode & Adversarial Test Coverage

The following failure modes are proven by automated unit tests in [`backend/tests/assistant/`](file:///D:/Documents/New%20folder/Finance-Complaints-Medallion-main/backend/tests/assistant/):

1. **Fabricated Numbers (`test_chat_triggers_fallback_when_model_fabricates_numbers`):** Model returning fabricated count `999,999` is rejected; output is replaced with grounded fallback containing `62,516`.
2. **Provider Down / 503 (`test_disabled_llm_client_raises_unavailable`):** Raises `LLM_UNAVAILABLE` or routes to degraded mode.
3. **Upstream Rate Limit / 429 (`test_fake_llm_client_failure_injections`):** Raises `LLMRateLimitError` mapping to HTTP 429.
4. **Upstream Timeout / 504 (`test_fake_llm_client_failure_injections`):** Raises `LLMTimeoutError` mapping to HTTP 504.
5. **Daily Quota Exhaustion (`test_budget_exhaustion_returns_429`):** Rejects requests exceeding `AI_DAILY_REQUEST_CAP` with 429 `AI_BUDGET_EXHAUSTED`.
6. **Prompt Injection (`test_prompt_injection_safety`):** Hostile prompts attempting SQL injection or system prompt extraction are treated as plain text and safely handled.
7. **Log Confidentiality (`test_safe_logging_never_logs_question_text_or_secrets`):** When `LOG_AI_PROMPTS=False`, questions and secrets are never emitted to application logs.
