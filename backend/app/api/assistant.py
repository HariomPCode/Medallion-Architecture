"""
backend/app/api/assistant.py
----------------------------
API endpoints for AI assistant configuration and chat (§13.3, §14).
- GET /api/v1/assistant/config
- POST /api/v1/assistant/chat
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_current_snapshot
from app.assistant.orchestrator import AssistantOrchestrator
from app.core.config import Settings, get_settings
from app.data.snapshot import Snapshot
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["Assistant"])


def get_orchestrator(
    raw_request: Request,
    settings: Settings = Depends(get_settings),
) -> AssistantOrchestrator:
    """Dependency helper to create or retrieve orchestrator instance."""
    app_settings = getattr(raw_request.app.state, "settings", None) or settings
    return AssistantOrchestrator(settings=app_settings)


@router.get(
    "/config",
    response_model=AssistantConfigResponse,
    summary="Get AI Assistant configuration and suggested questions",
    description="Returns assistant availability, current mode (llm or degraded), limits, and curated suggested questions.",
)
def get_assistant_config(
    orchestrator: AssistantOrchestrator = Depends(get_orchestrator),
) -> AssistantConfigResponse:
    return orchestrator.get_config()


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Chat with the AI Assistant",
    description="Submit a question to the grounded assistant. Operates across 8 read-only analytical tools with strict numeric grounding.",
)
async def chat_with_assistant(
    request: AssistantChatRequest,
    raw_request: Request,
    response: Response,
    snapshot: Snapshot = Depends(get_current_snapshot),
    orchestrator: AssistantOrchestrator = Depends(get_orchestrator),
) -> AssistantChatResponse:
    # Ensure responses are never cached (§13.3, §1216)
    response.headers["Cache-Control"] = "no-store"

    # Extract request ID from state or header
    request_id = getattr(raw_request.state, "request_id", None) or raw_request.headers.get(
        "X-Request-ID", "unknown"
    )

    return await orchestrator.handle_chat(
        request=request,
        snapshot=snapshot,
        request_id=request_id,
    )
