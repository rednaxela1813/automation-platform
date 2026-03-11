#!/usr/bin/env python3
"""Entrypoint script for starting the Email Automation Platform API server."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn

project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from automation.config.logging import configure_logging  # noqa: E402
from automation.config.settings import settings  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    """Run FastAPI server using configured settings."""
    logger.info("Starting Email Automation Platform on %s:%s", settings.host, settings.port)
    logger.info("API docs: http://%s:%s/docs", settings.host, settings.port)
    logger.info("Debug mode: %s", settings.debug)

    uvicorn.run(
        "automation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        reload_dirs=["src"] if settings.debug else None,
        log_level="info",
    )


if __name__ == "__main__":
    main()
