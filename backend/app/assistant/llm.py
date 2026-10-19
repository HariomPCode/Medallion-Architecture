"""
backend/app/assistant/llm.py
----------------------------
Provider-independent LLM client abstraction and implementations:
- DisabledLLMClient: Raises LLMUnavailableError.
- FakeLLMClient: Scripted deterministic provider supporting failure injections.
- AzureOpenAIClient: Production client calling Azure OpenAI / AI Foundry with sanitized error mapping.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable

from app.core.config import Settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)


class LLMUnavailableError(AppError):
    """Raised when the LLM service is disabled or unreachable."""

    def __init__(self, message: str = "AI Assistant language model is currently unavailable."):
        super().__init__(message=message, status_code=503, code="LLM_UNAVAILABLE")


class LLMTimeoutError(AppError):
    """Raised when the LLM call times out."""

    def __init__(
        self, message: str = "AI Assistant request timed out while contacting language model."
    ):
        super().__init__(message=message, status_code=504, code="LLM_TIMEOUT")


class LLMRateLimitError(AppError):
    """Raised when the upstream LLM returns a 429 rate limit."""

    def __init__(
        self,
        message: str = "Upstream AI service rate limit reached. Please retry in a few moments.",
    ):
        super().__init__(message=message, status_code=429, code="LLM_RATE_LIMIT")


@dataclass
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    content: Optional[str] = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    usage: LLMUsage = field(default_factory=LLMUsage)


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for provider-independent language model interaction."""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_output_tokens: int = 700,
        timeout: int = 20,
    ) -> LLMResponse: ...


class DisabledLLMClient:
    """Fallback client when LLM_PROVIDER is 'disabled'."""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_output_tokens: int = 700,
        timeout: int = 20,
    ) -> LLMResponse:
        raise LLMUnavailableError("AI Assistant language model is disabled in configuration.")


class FakeLLMClient:
    """
    Scripted, deterministic LLM client for testing and offline environments.
    Supports failure injection to test retry, timeout, rate-limiting, and grounding fallback.
    """

    def __init__(
        self,
        inject_timeout: bool = False,
        inject_429: bool = False,
        inject_malformed_tool_args: bool = False,
        inject_fabricated_numbers: bool = False,
        inject_unsupported: bool = False,
        inject_server_error: bool = False,
    ) -> None:
        self.inject_timeout = inject_timeout
        self.inject_429 = inject_429
        self.inject_malformed_tool_args = inject_malformed_tool_args
        self.inject_fabricated_numbers = inject_fabricated_numbers
        self.inject_unsupported = inject_unsupported
        self.inject_server_error = inject_server_error
        self.call_count: int = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_output_tokens: int = 700,
        timeout: int = 20,
    ) -> LLMResponse:
        self.call_count += 1

        if self.inject_timeout:
            await asyncio.sleep(0.01)
            raise LLMTimeoutError()

        if self.inject_429:
            raise LLMRateLimitError()

        if self.inject_server_error:
            raise LLMUnavailableError("Simulated upstream 500 internal server error")

        # Inspect messages to identify stage: Call #1 (tool routing) or Call #2 (narrative synthesis)
        user_question = ""
        last_tool_result: Optional[dict[str, Any]] = None

        for msg in messages:
            role = msg.get("role")
            if role == "user":
                user_question = str(msg.get("content", ""))
            elif role == "tool":
                try:
                    last_tool_result = json.loads(str(msg.get("content", "{}")))
                except Exception:
                    last_tool_result = {"raw": msg.get("content")}

        # Call #2: Tool result has been returned; synthesize grounded narrative
        if last_tool_result is not None:
            return self._synthesize_narrative(last_tool_result)

        # Call #1: Determine tool call from user question
        q_lower = user_question.lower()

        # Check for unsupported questions (company names, causes, forecasting, legal advice)
        unsupported_keywords = [
            "company",
            "wells fargo",
            "bank of america",
            "chase",
            "citibank",
            "equifax",
            "who is to blame",
            "why did",
            "cause",
            "forecast",
            "future",
            "predict",
            "lawyer",
            "legal advice",
            "sue",
        ]
        if self.inject_unsupported or any(kw in q_lower for kw in unsupported_keywords):
            return LLMResponse(
                content=(
                    "UNSUPPORTED: This dataset contains aggregated complaints without specific company names, "
                    "causation narratives, or forecasting data. Available data covers 5 financial categories, "
                    "9 sub-categories, channels, states, and timeliness outcomes from May 2017 to August 2023."
                ),
                tool_calls=[],
                usage=LLMUsage(prompt_tokens=50, completion_tokens=45, total_tokens=95),
            )

        # Map to appropriate tool
        tool_call = self._route_tool(q_lower)
        return LLMResponse(
            content=None,
            tool_calls=[tool_call],
            usage=LLMUsage(prompt_tokens=80, completion_tokens=25, total_tokens=105),
        )

    def _route_tool(self, q_lower: str) -> LLMToolCall:
        """Route user query to appropriate tool call."""
        if self.inject_malformed_tool_args:
            return LLMToolCall(
                id="call_mock_malformed",
                name="compare_categories",
                arguments={"group_by": "invalid_dimension", "sort": "bogus"},
            )

        # 1. T7: List anomalies (must check before explain or generic anomaly questions)
        if (
            "anomal" in q_lower
            and (
                "list" in q_lower
                or "show" in q_lower
                or "flagged" in q_lower
                or "records" in q_lower
            )
            and not ("how many" in q_lower or "score" in q_lower)
        ):
            return LLMToolCall(
                id="call_mock_anomalies",
                name="list_anomalies",
                arguments={"limit": 10},
            )

        # 2. T6: Quality summary
        if (
            "quality" in q_lower
            or "health" in q_lower
            or "completeness" in q_lower
            or "validity" in q_lower
            or "isolation forest" in q_lower
            or (
                "anomal" in q_lower
                and ("how many" in q_lower or "score" in q_lower or "rate" in q_lower)
            )
        ):
            return LLMToolCall(
                id="call_mock_quality",
                name="get_quality_summary",
                arguments={},
            )

        # 3. T8: Explain metric
        if (
            re.search(r"\bm-0\d\b", q_lower)
            or re.search(r"\bm-1\d\b", q_lower)
            or (
                "metric" in q_lower
                and (
                    "explain" in q_lower
                    or "definition" in q_lower
                    or "formula" in q_lower
                    or "measure" in q_lower
                )
            )
            or ("difference between" in q_lower and "rate" in q_lower)
            or ("how is" in q_lower and "defined" in q_lower)
        ):
            metric_id = "M-03"
            if "m-04" in q_lower or "legacy" in q_lower:
                metric_id = "M-04"
            elif "m-09" in q_lower or "routing" in q_lower or "days submitted" in q_lower:
                metric_id = "M-09"
            elif "m-11" in q_lower or "score" in q_lower:
                metric_id = "M-11"
            elif "m-10" in q_lower:
                metric_id = "M-10"
            return LLMToolCall(
                id="call_mock_explain",
                name="explain_metric",
                arguments={"metric_id": metric_id},
            )

        # 4. T5: Search complaints
        complaint_id_match = re.search(r"\b(\d{7,10})\b", q_lower)
        if "complaint" in q_lower and (
            "search" in q_lower or "lookup" in q_lower or "find" in q_lower or complaint_id_match
        ):
            cid = complaint_id_match.group(1) if complaint_id_match else None
            args: dict[str, Any] = {"limit": 10}
            if cid:
                args["complaint_id"] = cid
            return LLMToolCall(
                id="call_mock_search",
                name="search_complaints",
                arguments=args,
            )

        # 5. T3: Trends / time series
        if (
            "trend" in q_lower
            or "over time" in q_lower
            or "yearly" in q_lower
            or "year-over-year" in q_lower
            or "yoy" in q_lower
            or "growth" in q_lower
            or "partial year" in q_lower
            or re.search(r"\b20(17|18|19|20|21|22|23)\b", q_lower)
        ):
            return LLMToolCall(
                id="call_mock_trend",
                name="get_trend",
                arguments={"grain": "year", "group_by": "none"},
            )

        # 6. T2: Compare categories / sub-categories
        cat_keywords = [
            "category",
            "categories",
            "compare",
            "highest",
            "most",
            "banking",
            "payments",
            "collections",
            "lending",
            "credit reporting",
            "deposit accounts",
            "card products",
            "real estate lending",
            "money movement",
            "secured lending",
            "short-term lending",
            "education lending",
        ]
        if any(kw in q_lower for kw in cat_keywords):
            subcat_keywords = [
                "deposit accounts",
                "card products",
                "real estate lending",
                "money movement",
                "secured lending",
                "short-term lending",
                "education lending",
                "sub-category",
                "subcategory",
            ]
            group_by = (
                "sub_category" if any(skw in q_lower for skw in subcat_keywords) else "category"
            )
            return LLMToolCall(
                id="call_mock_categories",
                name="compare_categories",
                arguments={"group_by": group_by, "sort": "total"},
            )

        # 7. T4: Breakdown by dimension
        if (
            "channel" in q_lower
            or "submitted via" in q_lower
            or "by state" in q_lower
            or "company response" in q_lower
            or "company_response" in q_lower
        ):
            dim = "submitted_via"
            if "state" in q_lower:
                dim = "state"
            elif "company" in q_lower or "response" in q_lower:
                dim = "company_response"
            return LLMToolCall(
                id="call_mock_breakdown",
                name="get_breakdown",
                arguments={"dimension": dim, "limit": 10},
            )

        # 8. T1: Default to dataset overview
        return LLMToolCall(
            id="call_mock_overview",
            name="get_dataset_overview",
            arguments={},
        )

    def _synthesize_narrative(self, tool_envelope: dict[str, Any]) -> LLMResponse:
        """Synthesize a strictly grounded narrative from tool results."""
        if self.inject_fabricated_numbers:
            return LLMResponse(
                content="There are 999,999 complaints in total with a timely response rate of 12.34% and 555 anomalies.",
                tool_calls=[],
                usage=LLMUsage(prompt_tokens=150, completion_tokens=35, total_tokens=185),
            )

        tool_name = tool_envelope.get("tool", "")
        result = tool_envelope.get("result", {})

        if tool_name == "get_dataset_overview":
            total = result.get("total_complaints", 0)
            timely = result.get("timely", {})
            rate = timely.get("rate")
            denom = timely.get("rate_denominator", 0)
            yes_count = timely.get("yes", 0)
            no_count = timely.get("no", 0)
            in_prog = result.get("in_progress_count", 0)
            narrative = (
                f"The dataset contains {total:,} total complaints spanning from May 2017 to August 2023. "
                f"Across {denom:,} cases with recorded outcomes, the timely response rate is {rate}%. "
                f"Specifically, {yes_count:,} complaints had timely responses marked Yes, and {no_count:,} marked No. "
                f"There are {in_prog:,} open cases currently in progress."
            )
        elif tool_name == "compare_categories":
            items = result.get("items", [])
            group_by = result.get("group_by", "category")
            if items:
                lines = []
                for it in items:
                    name = it.get("category") or it.get("sub_category") or "Unknown"
                    tot = it.get("total", 0)
                    sh = it.get("share_pct", 0)
                    tr = it.get("timely_rate")
                    tr_str = f" with timely response rate {tr}%" if tr is not None else ""
                    lines.append(f"{name}: {tot:,} complaints ({sh}% share{tr_str})")
                narrative = f"Comparison across {group_by}s: " + "; ".join(lines) + "."
            else:
                narrative = "No complaint records match the specified filters."
        elif tool_name == "get_trend":
            total_series = result.get("total_series", {}).get("points", [])
            if total_series:
                first = total_series[0]
                last = total_series[-1]
                y2018: dict[str, Any] = next(
                    (p for p in total_series if p.get("period") == "2018"), {}
                )
                y2019: dict[str, Any] = next(
                    (p for p in total_series if p.get("period") == "2019"), {}
                )
                y2020: dict[str, Any] = next(
                    (p for p in total_series if p.get("period") == "2020"), {}
                )
                y2021: dict[str, Any] = next(
                    (p for p in total_series if p.get("period") == "2021"), {}
                )
                y2022: dict[str, Any] = next(
                    (p for p in total_series if p.get("period") == "2022"), {}
                )
                narrative = (
                    f"Annual complaint volume started in {first.get('period')} (partial year) with {first.get('total', 0):,} records. "
                    f"Between complete years 2018 and 2022, volumes were {y2018.get('total', 0):,} in 2018, "
                    f"{y2019.get('total', 0):,} in 2019, {y2020.get('total', 0):,} in 2020 (a {y2020.get('yoy_change_pct')}% YoY change), "
                    f"{y2021.get('total', 0):,} in 2021 (a {y2021.get('yoy_change_pct')}% YoY growth), "
                    f"and peaking in 2022 with {y2022.get('total', 0):,} complaints. "
                    f"Coverage concluded in {last.get('period')} (partial year) with {last.get('total', 0):,} complaints."
                )
            else:
                narrative = "No trend data points match the active filters."
        elif tool_name == "get_breakdown":
            dim = result.get("dimension", "dimension")
            items = result.get("items", [])
            top = items[0] if items else {}
            narrative = (
                f"Breakdown by {dim}: top item is {top.get('name', 'N/A')} with {top.get('total', 0):,} complaints, "
                f"representing {top.get('share_pct', 0)}% of the filtered total."
            )
        elif tool_name == "explain_metric":
            mid = result.get("metric_id", "")
            lbl = result.get("label", "")
            formula = result.get("formula_text", "")
            denom = result.get("denominator", "")
            bv = result.get("baseline_values", {})
            if mid == "M-03" and "baseline_denominator" in bv:
                narrative = (
                    f"{lbl} ({mid}) is calculated as: {formula}. The denominator is: {denom}. "
                    f"In our dataset, this evaluates across {bv['baseline_denominator']:,} resolved cases with a rate of {bv.get('baseline_rate')}%. "
                    "Open cases are excluded from the denominator."
                )
            elif mid == "M-04" and "baseline_denominator" in bv:
                narrative = (
                    f"{lbl} ({mid}) is calculated as: {formula}. The denominator is: {denom}. "
                    f"Unlike primary rate M-03 (denominator {bv.get('primary_denominator', 61022):,}), legacy rate M-04 includes all {bv['baseline_denominator']:,} complaints "
                    f"in its denominator, yielding {bv.get('baseline_rate')}%. It understates compliance by penalizing active cases."
                )
            elif mid == "M-09":
                narrative = (
                    f"{lbl} ({mid}) is calculated as: {formula}. "
                    "It measures the intake routing lag from complaint submission to receipt by the CFPB, "
                    "and does not measure company response time."
                )
            else:
                narrative = (
                    f"{lbl} ({mid}) is calculated as: {formula}. The denominator is: {denom}."
                )
        elif tool_name == "get_quality_summary":
            score = result.get("overall_quality_score", 0)
            status = result.get("status", "")
            flagged = result.get("anomalies", {}).get("flagged", 0)
            rate_pct = result.get("anomalies", {}).get("rate_pct", 0)
            narrative = (
                f"The composite pipeline data quality score is {score} ({status}). "
                f"Isolation Forest identified {flagged:,} statistically unusual records ({rate_pct}% of total records)."
            )
        elif tool_name == "list_anomalies":
            total = result.get("total", 0)
            count = len(result.get("items", []))
            narrative = (
                f"Retrieved {count} flagged anomalous records out of {total:,} total flagged cases. "
                "These records represent statistical outliers identified by the Isolation Forest model."
            )
        elif tool_name == "search_complaints":
            total = result.get("total", 0)
            narrative = f"Found {total:,} complaint records matching the specified criteria."
        else:
            narrative = "Analysis completed based on the retrieved dataset evidence."

        return LLMResponse(
            content=narrative,
            tool_calls=[],
            usage=LLMUsage(prompt_tokens=120, completion_tokens=40, total_tokens=160),
        )


class AzureOpenAIClient:
    """
    Production Azure OpenAI client.
    Initialized per current Azure OpenAI Python SDK specifications (Microsoft Learn, updated 2024-2026).
    Uses AsyncAzureOpenAI with sanitized error handling and bounded retries (§14.2, §22).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.endpoint = settings.LLM_ENDPOINT.strip()
        self.deployment = settings.LLM_DEPLOYMENT.strip()
        self.api_version = settings.LLM_API_VERSION.strip()
        self.auth_mode = settings.LLM_AUTH_MODE
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncAzureOpenAI
        except ImportError as exc:
            raise LLMUnavailableError(
                "The 'openai' library is required to use Azure OpenAI client."
            ) from exc

        if not self.endpoint:
            raise LLMUnavailableError("LLM_ENDPOINT must be configured to use Azure OpenAI.")
        if not self.deployment:
            raise LLMUnavailableError("LLM_DEPLOYMENT must be configured to use Azure OpenAI.")

        if self.auth_mode == "entra":
            try:
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider

                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                self._client = AsyncAzureOpenAI(
                    azure_endpoint=self.endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=self.api_version,
                )
            except Exception as exc:
                logger.error("Failed to configure Entra ID token provider for Azure OpenAI")
                raise LLMUnavailableError(
                    "Failed to authenticate to Azure OpenAI via Entra ID."
                ) from exc
        else:
            if not self.settings.LLM_API_KEY:
                raise LLMUnavailableError(
                    "LLM_API_KEY must be provided when LLM_AUTH_MODE='api_key'."
                )
            self._client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.settings.LLM_API_KEY,
                api_version=self.api_version,
            )

        return self._client

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_output_tokens: int = 700,
        timeout: int = 20,
    ) -> LLMResponse:
        import openai

        client = self._get_client()

        # Build kwargs
        kwargs: dict[str, Any] = {
            "model": self.deployment,
            "messages": messages,
            "max_tokens": max_output_tokens,
            "temperature": 0.1,  # Keep low per §14.2
            "timeout": timeout,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # Retry once on 429/5xx with backoff per §14.2
        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                raw_response = await client.chat.completions.create(**kwargs)
                choice = raw_response.choices[0]
                message = choice.message

                tool_calls: list[LLMToolCall] = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        try:
                            parsed_args = json.loads(tc.function.arguments)
                        except Exception:
                            parsed_args = {"_raw": tc.function.arguments}
                        tool_calls.append(
                            LLMToolCall(
                                id=tc.id,
                                name=tc.function.name,
                                arguments=parsed_args,
                            )
                        )

                usage = LLMUsage()
                if raw_response.usage:
                    usage = LLMUsage(
                        prompt_tokens=raw_response.usage.prompt_tokens,
                        completion_tokens=raw_response.usage.completion_tokens,
                        total_tokens=raw_response.usage.total_tokens,
                    )

                return LLMResponse(
                    content=message.content,
                    tool_calls=tool_calls,
                    usage=usage,
                )

            except openai.RateLimitError as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                raise LLMRateLimitError() from None

            except openai.APITimeoutError as exc:
                last_error = exc
                raise LLMTimeoutError() from None

            except (openai.APIConnectionError, openai.InternalServerError) as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                logger.error("Azure OpenAI communication failed after retry")
                raise LLMUnavailableError(
                    "Azure OpenAI service connection failed. Please retry later."
                ) from None

            except openai.APIStatusError as exc:
                last_error = exc
                logger.error(
                    "Azure OpenAI returned error status: %s", getattr(exc, "status_code", "unknown")
                )
                raise LLMUnavailableError(
                    f"Azure OpenAI service error (status {getattr(exc, 'status_code', 500)})."
                ) from None

            except Exception as exc:
                last_error = exc
                logger.error("Unexpected error in Azure OpenAI client")
                raise LLMUnavailableError(
                    "Unexpected error communicating with AI service."
                ) from None

        raise LLMUnavailableError("Azure OpenAI request failed.") from last_error


def get_llm_client(settings: Settings) -> LLMClient:
    """Factory creating LLM client according to active Settings."""
    provider = settings.LLM_PROVIDER
    if provider == "azure_openai":
        return AzureOpenAIClient(settings=settings)
    elif provider == "fake":
        return FakeLLMClient()
    else:
        return DisabledLLMClient()
