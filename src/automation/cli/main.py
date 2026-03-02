"""Command-line entrypoint for Email Automation Platform."""

from __future__ import annotations

import uvicorn

from automation.config.settings import settings


def main() -> None:
    """Run FastAPI server using configured host/port/debug settings."""
    uvicorn.run(
        "automation.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )

