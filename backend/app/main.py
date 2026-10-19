"""
backend/app/main.py
-------------------
FastAPI application factory and lifecycle management per §11, §12, and §13.
Implements production safeguards, security middleware, rate limiting, and CORS controls.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIDMiddleware, configure_logging
from app.core.ratelimit import register_rate_limiting
from app.core.security import (
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
    verify_internal_api_key,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and graceful shutdown."""
    settings = app.state.settings
    configure_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

    # Initialize data snapshot manager if available
    try:
        from app.data.snapshot import get_snapshot_manager

        manager = get_snapshot_manager(settings)
        await manager.startup_load()
    except Exception as exc:
        # If in fixture/local_snapshot mode and load fails, fail fast unless in test
        if settings.APP_ENV != "test" and settings.DATA_MODE in ("fixture", "local_snapshot"):
            import logging

            logging.getLogger("app.main").error("Fatal data load failure on startup: %s", exc)
            # Re-raise to prevent startup on bad offline config
            raise

    yield

    # Teardown logic
    try:
        from app.data.snapshot import get_snapshot_manager

        manager = get_snapshot_manager()
        await manager.shutdown()
    except Exception:
        pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory for FastAPI."""
    app_settings = settings or get_settings()

    app = FastAPI(
        title="Finance Complaints Medallion API",
        description="Grounded AI & Analytics API for CFPB Financial Consumer Complaints",
        version="1.0.0",
        docs_url="/docs" if app_settings.APP_ENV != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if app_settings.APP_ENV != "production" else None,
        lifespan=lifespan,
        dependencies=[Depends(verify_internal_api_key)],
    )

    app.state.settings = app_settings

    # 1. Register custom error handlers
    register_error_handlers(app)

    # 2. Register rate limiting state, handler, and middleware
    register_rate_limiting(app)

    # 3. Security headers middleware (nosniff, DENY, strict-origin, cache headers)
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Request body size limit middleware (enforces MAX_REQUEST_BYTES -> 413)
    app.add_middleware(RequestBodyLimitMiddleware, max_bytes=app_settings.MAX_REQUEST_BYTES)

    # 5. Register CORS middleware with explicit origins, no credentials, restricted headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID", "X-Internal-Key"],
        expose_headers=[
            "X-Request-ID",
            "Retry-After",
            "X-Export-Truncated",
            "X-Export-Row-Count",
        ],
    )

    # 6. Register Request-ID middleware (must be outermost to track all requests)
    app.add_middleware(RequestIDMiddleware)

    # 7. Mount API routers
    app.include_router(health.router)
    from app.api import analytics, assistant, complaints, dashboard, meta, quality

    app.include_router(meta.router)
    app.include_router(dashboard.router)
    app.include_router(analytics.router)
    app.include_router(complaints.router)
    app.include_router(quality.router)
    app.include_router(assistant.router)

    return app


# Root application instance for ASGI servers
app = create_app()
