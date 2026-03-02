"""FastAPI application entry point for Email Automation Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automation.api.routers import router as api_router
from automation.config.settings import settings
from automation.web.interface import web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the FastAPI application."""
    # Startup: create required directories
    Path(settings.safe_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.quarantine_dir).mkdir(parents=True, exist_ok=True)

    print(f"🚀 {settings.app_name} startup complete")
    yield
    # Shutdown
    print("📧 Email Automation Platform shutdown")


def create_app() -> FastAPI:
    """Factory function for creating the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Automated email processing with attachments",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(web_router)  # Web interface without prefix

    return app


# Create application instance
app = create_app()


@app.get("/api")
async def root():
    """API information."""
    return {
        "message": "Email Automation Platform API",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "web_interface": "/",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}
