"""
backend/app/assistant/orchestrator.py
-------------------------------------
Core orchestrator for the AI assistant (§14.2).
Coordinates input sanitization, budget checks, tool invocation, repair retries,
grounding validation, degraded mode, and deterministic fallback rendering.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Literal, Optional

from app.assistant.budget import BudgetTracker, get_budget_tracker
from app.assistant.grounding import generate_data_blocks, render_fallback, verify_grounding
from app.assistant.llm import (
    LLMClient,
    LLMResponse,
    LLMToolCall,
    LLMUnavailableError,
    get_llm_client,
)
from app.assistant.prompts import SYSTEM_PROMPT, get_openai_tools
from app.assistant.tools import ToolArgumentError, execute_tool
from app.core.config import Settings
from app.data.snapshot import Snapshot
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
    AssistantLimits,
    ChatMessage,
    DataBlock,
    EvidenceItem,
    GroundingInfo,
    SuggestedQuestion,
)

logger = logging.getLogger(__name__)

# Curated suggested questions with stable IDs (§14.6)
SUGGESTED_QUESTIONS: list[SuggestedQuestion] = [
    SuggestedQuestion(
        id="sq_overview",
        text="What is the total number of complaints and the timely response rate across the dataset?",
        tool_hint="get_dataset_overview",
    ),
    SuggestedQuestion(
        id="sq_top_category",
        text="Which financial product category received the highest volume of consumer complaints?",
        tool_hint="compare_categories",
    ),
    SuggestedQuestion(
        id="sq_trends",
        text="How did complaint volume trend year-over-year between 2018 and 2022?",
        tool_hint="get_trend",
    ),
    SuggestedQuestion(
        id="sq_channels",
        text="What are the most common submission channels consumers use to file complaints?",
        tool_hint="get_breakdown",
    ),
    SuggestedQuestion(
        id="sq_dq",
        text="What is the overall data quality composite score and what are its key limitations?",
        tool_hint="get_quality_summary",
    ),
    SuggestedQuestion(
        id="sq_timely_def",
        text="How is the primary timely response rate calculated and how does it differ from the legacy rate?",
        tool_hint="explain_metric",
    ),
]

# Static dataset limitations surfaced in answers (§14.4)
DATASET_LIMITATIONS: list[str] = [
    "Dataset contains 62,516 complaints from May 2017 to August 2023 across 5 financial categories.",
    "Specific company names, consumer narratives, and root-cause explanations are not present in this dataset.",
    "Years 2017 and 2023 are partial periods; annual YoY comparisons are computed only between 2018 and 2022.",
    "Days submitted to received measures CFPB routing lag, not company response time.",
    "ML Normality score is derived from the fixed 5% contamination parameter of the Isolation Forest model.",
]


class AssistantOrchestrator:
    """Orchestrates question answering with strict grounding verification."""

    def __init__(
        self,
        settings: Settings,
        llm_client: Optional[LLMClient] = None,
        budget_tracker: Optional[BudgetTracker] = None,
    ) -> None:
        self.settings = settings
        self.llm_client = llm_client or get_llm_client(settings)
        self.budget_tracker = budget_tracker or get_budget_tracker(
            daily_cap=settings.AI_DAILY_REQUEST_CAP
        )

    def get_config(self) -> AssistantConfigResponse:
        """Return assistant configuration, mode, limits, and suggested questions."""
        provider = self.settings.LLM_PROVIDER
        available = provider != "disabled"
        mode: Literal["llm", "degraded"] = (
            "llm" if provider in ("azure_openai", "fake") else "degraded"
        )
        return AssistantConfigResponse(
            available=available,
            mode=mode,
            suggested_questions=SUGGESTED_QUESTIONS,
            limits=AssistantLimits(
                max_question_chars=self.settings.AI_MAX_QUESTION_CHARS,
                max_history_turns=self.settings.AI_HISTORY_MAX_MESSAGES,
                daily_request_cap=self.settings.AI_DAILY_REQUEST_CAP,
                max_output_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS,
            ),
        )

    def _sanitize_text(self, text: str) -> str:
        """Strip control characters while preserving standard whitespace."""
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text).strip()

    def _prepare_history(self, history: list[ChatMessage]) -> list[dict[str, str]]:
        """Trim and sanitize conversation history (<= 6 messages, <= 2000 chars each)."""
        trimmed = history[-self.settings.AI_HISTORY_MAX_MESSAGES :]
        return [
            {"role": msg.role, "content": self._sanitize_text(msg.content[:2000])}
            for msg in trimmed
        ]

    async def handle_chat(
        self,
        request: AssistantChatRequest,
        snapshot: Snapshot,
        request_id: str,
    ) -> AssistantChatResponse:
        """
        Process chat request through the full grounded orchestrator loop (§14.2).
        Enforces budget, safety, degraded mode, tools, grounding, and fallback.
        """
        start_time = time.monotonic()

        # 1. Budget and daily cap verification
        self.budget_tracker.check_and_increment()

        # 2. Input sanitization and length check
        clean_question = self._sanitize_text(request.question)
        if not clean_question:
            clean_question = "What is the dataset overview?"

        history_msgs = self._prepare_history(request.history)

        # 3. Check for degraded / offline execution mode
        is_llm_disabled = self.settings.LLM_PROVIDER == "disabled"
        if is_llm_disabled:
            return self._handle_degraded_request(request, snapshot, request_id, clean_question)

        # 4. First LLM Call: Tool routing & unsupported judgment
        tools_schema = get_openai_tools(snapshot)
        call1_messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history_msgs,
            {"role": "user", "content": clean_question},
        ]

        try:
            call1_resp: LLMResponse = await self.llm_client.chat(
                messages=call1_messages,
                tools=tools_schema,
                max_output_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS,
                timeout=self.settings.LLM_TIMEOUT_SECONDS,
            )
            self.budget_tracker.record_tokens(
                call1_resp.usage.prompt_tokens, call1_resp.usage.completion_tokens
            )
        except LLMUnavailableError:
            logger.warning(
                "LLM unavailable; falling back to degraded mode for request %s", request_id
            )
            return self._handle_degraded_request(request, snapshot, request_id, clean_question)

        # 5. Check if LLM flagged query as UNSUPPORTED
        content_text = call1_resp.content or ""
        if content_text.startswith("UNSUPPORTED:") or (
            "unsupported" in content_text.lower() and not call1_resp.tool_calls
        ):
            clean_msg = content_text.replace("UNSUPPORTED:", "").strip()
            if not clean_msg:
                clean_msg = (
                    "This question cannot be answered from the financial complaints dataset. "
                    "The dataset covers aggregated complaint counts, product categories, channels, "
                    "states, and timeliness from May 2017 to August 2023, without specific company names "
                    "or causal explanations."
                )
            return AssistantChatResponse(
                status="unsupported",
                answer_markdown=clean_msg,
                data_blocks=[],
                evidence=[],
                limitations=DATASET_LIMITATIONS,
                grounding=GroundingInfo(checked=True, ungrounded_numbers=0, fallback_used=False),
                request_id=request_id,
            )

        # 6. If no tool called, route to default overview tool
        tool_calls = call1_resp.tool_calls
        if not tool_calls:
            tool_calls = [
                LLMToolCall(id="call_fallback_overview", name="get_dataset_overview", arguments={})
            ]

        # Enforce AI_MAX_TOOL_CALLS cap (<= 3)
        tool_calls = tool_calls[: self.settings.AI_MAX_TOOL_CALLS]

        # 7. Execute tools and collect envelopes
        tool_envelopes: list[dict[str, Any]] = []
        tool_messages: list[dict[str, Any]] = []

        for tc in tool_calls:
            # Merge context_filters if present and not overridden
            merged_args = dict(tc.arguments)
            if request.context_filters:
                cf_dict = request.context_filters.model_dump(exclude_none=True)
                for k, v in cf_dict.items():
                    if k not in merged_args or merged_args[k] is None:
                        merged_args[k] = v

            try:
                envelope = execute_tool(tc.name, merged_args, snapshot)
            except ToolArgumentError as exc:
                logger.info(
                    "Tool execution failed for %s: %s; attempting single repair", tc.name, exc
                )
                # Attempt one argument-repair call per §14.2
                repair_messages = list(call1_messages)
                repair_messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                        ],
                    }
                )
                repair_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {
                                "error": str(exc),
                                "instruction": "Provide corrected arguments strictly matching schema.",
                            }
                        ),
                    }
                )
                try:
                    repair_resp = await self.llm_client.chat(
                        messages=repair_messages,
                        tools=tools_schema,
                        max_output_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS,
                        timeout=self.settings.LLM_TIMEOUT_SECONDS,
                    )
                    self.budget_tracker.record_tokens(
                        repair_resp.usage.prompt_tokens, repair_resp.usage.completion_tokens
                    )
                    if repair_resp.tool_calls:
                        envelope = execute_tool(
                            repair_resp.tool_calls[0].name,
                            repair_resp.tool_calls[0].arguments,
                            snapshot,
                        )
                    else:
                        envelope = execute_tool("get_dataset_overview", {}, snapshot)
                except Exception:
                    # Default safe fallback tool on failed repair
                    envelope = execute_tool("get_dataset_overview", {}, snapshot)

            tool_envelopes.append(envelope)
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(envelope),
                }
            )

        # 8. Second LLM Call: Generate narrative based on tool results
        call2_messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history_msgs,
            {"role": "user", "content": clean_question},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in tool_calls
                ],
            },
            *tool_messages,
        ]

        try:
            call2_resp: LLMResponse = await self.llm_client.chat(
                messages=call2_messages,
                max_output_tokens=self.settings.LLM_MAX_OUTPUT_TOKENS,
                timeout=self.settings.LLM_TIMEOUT_SECONDS,
            )
            self.budget_tracker.record_tokens(
                call2_resp.usage.prompt_tokens, call2_resp.usage.completion_tokens
            )
            raw_narrative = call2_resp.content or ""
        except Exception as exc:
            logger.warning("Call #2 narrative generation failed (%s); using fallback renderer", exc)
            raw_narrative = render_fallback(tool_envelopes, snapshot)

        # 9. Strict Numeric Grounding Check (§14.5)
        grounding_result = verify_grounding(raw_narrative, tool_envelopes, snapshot)
        fallback_used = False
        final_narrative = raw_narrative

        if not grounding_result.is_grounded:
            logger.warning(
                "Grounding check failed for request %s (ungrounded tokens: %s). Replacing with deterministic fallback.",
                request_id,
                grounding_result.ungrounded_numbers,
            )
            final_narrative = render_fallback(tool_envelopes, snapshot)
            fallback_used = True
            # Re-verify fallback to ensure 100% compliance
            recheck = verify_grounding(final_narrative, tool_envelopes, snapshot)
            ungrounded_count = len(recheck.ungrounded_numbers)
        else:
            ungrounded_count = 0

        # 10. Assemble structured data blocks and evidence
        data_blocks_raw = generate_data_blocks(tool_envelopes, snapshot)
        data_blocks = [DataBlock(**b) for b in data_blocks_raw]

        evidence_items: list[EvidenceItem] = []
        for tr in tool_envelopes:
            prov = tr.get("provenance", {})
            evidence_items.append(
                EvidenceItem(
                    tool=tr.get("tool", ""),
                    arguments=tr.get("arguments", {}),
                    metric_ids=prov.get("metric_ids", []),
                    dataset_origin=prov.get("data_origin", "local_snapshot"),
                    pipeline_refreshed_at=prov.get("pipeline_refreshed_at", "2026-09-17T05:50:00Z"),
                )
            )

        duration_ms = (time.monotonic() - start_time) * 1000
        if self.settings.LOG_AI_PROMPTS:
            logger.info(
                "Chat request %s processed in %.1fms (status=answered, fallback=%s, question=%r)",
                request_id,
                duration_ms,
                fallback_used,
                clean_question,
            )
        else:
            logger.info(
                "Chat request %s processed in %.1fms (status=answered, fallback=%s, tools=%s)",
                request_id,
                duration_ms,
                fallback_used,
                [tr.get("tool") for tr in tool_envelopes],
            )

        return AssistantChatResponse(
            status="answered",
            answer_markdown=final_narrative,
            data_blocks=data_blocks,
            evidence=evidence_items,
            limitations=DATASET_LIMITATIONS,
            grounding=GroundingInfo(
                checked=True,
                ungrounded_numbers=ungrounded_count,
                fallback_used=fallback_used,
            ),
            request_id=request_id,
        )

    def _handle_degraded_request(
        self,
        request: AssistantChatRequest,
        snapshot: Snapshot,
        request_id: str,
        question_text: str,
    ) -> AssistantChatResponse:
        """
        Handle request when LLM is disabled or unavailable (§14.6).
        Maps suggested_question_id to deterministic tool execution + template renderer.
        """
        tool_name = "get_dataset_overview"
        tool_args: dict[str, Any] = {}

        if request.suggested_question_id:
            for sq in SUGGESTED_QUESTIONS:
                if sq.id == request.suggested_question_id:
                    if sq.tool_hint == "compare_categories":
                        tool_name = "compare_categories"
                        tool_args = {"group_by": "category", "sort": "total"}
                    elif sq.tool_hint == "get_trend":
                        tool_name = "get_trend"
                        tool_args = {"grain": "year", "group_by": "none"}
                    elif sq.tool_hint == "get_breakdown":
                        tool_name = "get_breakdown"
                        tool_args = {"dimension": "submitted_via", "limit": 10}
                    elif sq.tool_hint == "get_quality_summary":
                        tool_name = "get_quality_summary"
                        tool_args = {}
                    elif sq.tool_hint == "explain_metric":
                        tool_name = "explain_metric"
                        tool_args = {"metric_id": "M-03"}
                    break
        else:
            # Free-text question in degraded mode: return helpful guidance
            return AssistantChatResponse(
                status="degraded",
                answer_markdown=(
                    "The AI Assistant language model is currently disabled or unreachable. "
                    "In degraded mode, you can select any of the curated suggested questions below "
                    "to view authoritative, verified analytical tables and metrics."
                ),
                data_blocks=[],
                evidence=[],
                limitations=DATASET_LIMITATIONS,
                grounding=GroundingInfo(checked=True, ungrounded_numbers=0, fallback_used=True),
                request_id=request_id,
            )

        envelope = execute_tool(tool_name, tool_args, snapshot)
        fallback_narrative = render_fallback([envelope], snapshot)
        data_blocks_raw = generate_data_blocks([envelope], snapshot)
        data_blocks = [DataBlock(**b) for b in data_blocks_raw]

        prov = envelope.get("provenance", {})
        evidence_item = EvidenceItem(
            tool=tool_name,
            arguments=tool_args,
            metric_ids=prov.get("metric_ids", []),
            dataset_origin=prov.get("data_origin", "local_snapshot"),
            pipeline_refreshed_at=prov.get("pipeline_refreshed_at", "2026-09-17T05:50:00Z"),
        )

        return AssistantChatResponse(
            status="degraded",
            answer_markdown=f"[Degraded Mode Notice: Language model is offline. Answering via deterministic verified templates.]\n\n{fallback_narrative}",
            data_blocks=data_blocks,
            evidence=[evidence_item],
            limitations=DATASET_LIMITATIONS,
            grounding=GroundingInfo(checked=True, ungrounded_numbers=0, fallback_used=True),
            request_id=request_id,
        )
