"""Command-line entrypoint for Email Automation Platform."""

from __future__ import annotations

import logging

import uvicorn

from automation.config.logging import configure_logging
from automation.config.settings import settings

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    """Run FastAPI server using configured host/port/debug settings."""
    logger.info("Starting API server on %s:%s", settings.host, settings.port)
    uvicorn.run(
        "automation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
