"""
backend/app/api/health.py
-------------------------
Platform health and liveness endpoints (§13.2 #1 and #2).
"""

from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.errors import build_error_envelope
from app.core.logging import request_id_ctx
from app.core.ratelimit import limiter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Process liveness check")
@limiter.exempt
async def health_live(request: Request) -> dict[str, Any]:
    """Returns 200 if the process is running and accepting HTTP connections."""
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    req_id = (
        getattr(request.state, "request_id", None)
        or request_id_ctx.get()
        or request.headers.get("X-Request-ID", "")
    )
    return {
        "status": "alive",
        "app_env": settings.APP_ENV,
        "request_id": req_id,
    }


@router.get("/ready", summary="Data readiness check")
@limiter.exempt
async def health_ready(request: Request, response: Response) -> dict[str, Any]:
    """
    Returns 200 if a validated snapshot is loaded in memory.
    Returns 503 if data is unavailable or failing validation.
    """
    from app.data.snapshot import get_snapshot_manager  # lazy import

    manager = getattr(request.app.state, "snapshot_manager", None) or get_snapshot_manager()
    current_snapshot = manager.current_snapshot

    req_id = (
        getattr(request.state, "request_id", None)
        or request_id_ctx.get()
        or request.headers.get("X-Request-ID", "")
    )

    if current_snapshot is None or manager.status == "unavailable":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return build_error_envelope(
            code="DATA_UNAVAILABLE",
            message="No validated data snapshot is loaded in memory.",
            request_id=req_id,
            details={"status": manager.status},
        )

    return {
        "status": "ready",
        "data_status": manager.status,  # "fresh" or "stale"
        "row_count": len(current_snapshot.silver_complaints),
        "data_origin": current_snapshot.provenance.get("data_origin", "unknown"),
        "loaded_at": current_snapshot.loaded_at,
        "skew_warning": current_snapshot.skew_warning,
    }
