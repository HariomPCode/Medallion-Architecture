"""
backend/app/schemas/assistant.py
--------------------------------
Pydantic schemas for the AI assistant API (§13.3).
Defines request and response envelopes for /api/v1/assistant/config and /api/v1/assistant/chat.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.filters import ComplaintFilters


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list, max_length=6)
    suggested_question_id: Optional[str] = None
    context_filters: Optional[ComplaintFilters] = None


class DataBlock(BaseModel):
    type: Literal["table", "kpi", "series"]
    title: str
    columns: list[str]
    rows: list[list[Any]]
    source_tool: str
    dataset_as_of: str


class EvidenceItem(BaseModel):
    tool: str
    arguments: dict[str, Any]
    metric_ids: list[str]
    dataset_origin: str
    pipeline_refreshed_at: str


class GroundingInfo(BaseModel):
    checked: bool
    ungrounded_numbers: int
    fallback_used: bool


class AssistantChatResponse(BaseModel):
    status: Literal["answered", "unsupported", "degraded", "error"]
    answer_markdown: str
    data_blocks: list[DataBlock] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    grounding: GroundingInfo
    request_id: str


class SuggestedQuestion(BaseModel):
    id: str
    text: str
    tool_hint: Optional[str] = None


class AssistantLimits(BaseModel):
    max_question_chars: int = 500
    max_history_turns: int = 6
    daily_request_cap: int = 300
    max_output_tokens: int = 700


class AssistantConfigResponse(BaseModel):
    available: bool
    mode: Literal["llm", "degraded"]
    suggested_questions: list[SuggestedQuestion]
    limits: AssistantLimits
