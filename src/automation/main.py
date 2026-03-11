"""FastAPI application entry point for Email Automation Platform."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automation.api.endpoints.service import router as service_router
from automation.api.routers import router as api_router
from automation.config.logging import configure_logging
from automation.config.settings import settings
from automation.web.interface import web_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the FastAPI application."""
    Path(settings.safe_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.quarantine_dir).mkdir(parents=True, exist_ok=True)

    logger.info("%s startup complete", settings.app_name)
    yield
    logger.info("%s shutdown complete", settings.app_name)


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Automated email processing with attachments",
        debug=settings.debug,
        lifespan=lifespan,
    )

    cors_origins = settings.resolved_cors_allowed_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(service_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(web_router)
    return app


app = create_app()
