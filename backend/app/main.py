"""
backend/app/main.py
-------------------
FastAPI application factory and lifecycle management per §11 and §13.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIDMiddleware, configure_logging


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
        lifespan=lifespan,
    )

    app.state.settings = app_settings

    # 1. Register Request-ID middleware (must be outermost)
    app.add_middleware(RequestIDMiddleware)

    # 2. Register CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Register custom error handlers
    register_error_handlers(app)

    # 4. Mount API routers
    app.include_router(health.router)

    return app


# Root application instance for ASGI servers
app = create_app()
