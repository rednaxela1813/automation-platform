"""FastAPI application entry point for Email Automation Platform.

This module is responsible for assembling and configuring the FastAPI
application instance. It connects routers, configures middleware,
initializes logging, and defines lifecycle hooks that run during
startup and shutdown of the service.
"""

# Enables postponed evaluation of type annotations.
# Instead of resolving type hints immediately, Python stores them as strings.
# This improves compatibility with forward references and modern typing tools
# used by frameworks like FastAPI and Pydantic.
from __future__ import annotations

import logging

# asynccontextmanager allows us to implement the application lifecycle
# (startup and shutdown logic) using an async context manager pattern.
from contextlib import asynccontextmanager

# Path from pathlib is used for safe and cross-platform filesystem operations.
from pathlib import Path

# FastAPI is the main web framework class used to create the application object.
from fastapi import FastAPI

# CORSMiddleware enables Cross-Origin Resource Sharing configuration.
# This allows frontend applications hosted on different domains or ports
# to communicate with this backend API via browsers.
from fastapi.middleware.cors import CORSMiddleware


# Router that contains system/service endpoints
# such as health checks or API metadata.
from automation.api.endpoints.service import router as service_router

# Router that contains versioned API endpoints.
# These endpoints are typically consumed programmatically by other services
# or client applications.
from automation.api.routers import router as api_router

# Logging configuration function that sets up handlers, formatters,
# and logging levels for the application.
from automation.config.logging import configure_logging

# Centralized application settings (usually based on Pydantic BaseSettings).
# This object provides configuration such as:
# - application name and version
# - debug mode
# - allowed CORS origins
# - storage directories
from automation.config.settings import settings

# Router that serves the web interface or UI endpoints.
from automation.web.interface import web_router


# Create a module-level logger.
# Using __name__ ensures the logger name reflects the module path
# (e.g., "automation.main"), which helps with structured logging.
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the FastAPI application.

    This function defines code that runs when the application starts
    and when it shuts down.

    Everything before `yield` executes during application startup.
    Everything after `yield` executes during shutdown.

    Typical responsibilities of a lifecycle handler include:
    - preparing required directories
    - establishing database connections
    - initializing external services (Redis, message queues, etc.)
    - cleaning up resources during shutdown
    """

    # Ensure the directory used for storing processed or trusted files exists.
    # parents=True allows creating missing parent directories.
    # exist_ok=True prevents errors if the directory already exists.
    Path(settings.safe_storage_dir).mkdir(parents=True, exist_ok=True)

    # Ensure the quarantine directory exists.
    # This directory likely stores suspicious or unverified attachments
    # that require additional inspection before being processed.
    Path(settings.quarantine_dir).mkdir(parents=True, exist_ok=True)

    # Log application startup event.
    logger.info("%s startup complete", settings.app_name)

    # Yield control back to FastAPI.
    # After this point the application starts serving requests.
    yield

    # Code below runs when the application is shutting down.
    # Useful for cleanup tasks such as closing connections
    # or flushing logs.
    logger.info("%s shutdown complete", settings.app_name)


def create_app() -> FastAPI:
    """Factory function for creating and configuring the FastAPI application.

    Using an application factory pattern improves flexibility because:
    - the application can be instantiated multiple times in tests
    - configuration logic stays centralized
    - side effects during module import are minimized
    """

    # Initialize logging configuration for the application.
    # This typically sets log format, handlers (stdout/file),
    # and logging levels depending on the environment.
    configure_logging()

    # Create the FastAPI application instance.
    app = FastAPI(

        # Human-readable name shown in the generated OpenAPI documentation.
        title=settings.app_name,

        # Version of the service. Useful for diagnostics and API documentation.
        version=settings.app_version,

        # Description that appears in the API documentation (/docs).
        description="Automated email processing with attachments",

        # Enables debug features when running in development environments.
        debug=settings.debug,

        # Register lifecycle hooks for startup and shutdown events.
        lifespan=lifespan,
    )

    # Resolve the list of allowed CORS origins from configuration.
    # This allows environment-specific behavior (development vs production).
    cors_origins = settings.resolved_cors_allowed_origins()

    # Add the CORS middleware to the application.
    # Middleware intercepts requests before they reach route handlers.
    app.add_middleware(
        CORSMiddleware,

        # List of allowed origins (domains that can call this API).
        allow_origins=cors_origins,

        # Allow cookies and authentication headers to be sent
        # in cross-origin requests.
        allow_credentials=True,

        # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.).
        allow_methods=["*"],

        # Allow all request headers.
        allow_headers=["*"],
    )

    # Register system/service endpoints.
    # These typically include routes like /health or /api.
    app.include_router(service_router)

    # Register versioned API endpoints under /api/v1/*
    # This enables API versioning and better long-term compatibility.
    app.include_router(api_router, prefix="/api/v1")

    # Register web interface routes (usually HTML pages or UI endpoints).
    app.include_router(web_router)

    # Return the fully configured application instance.
    return app


# Create the actual FastAPI application instance.
# This variable is what ASGI servers (such as Uvicorn or Gunicorn)
# import when running the application:
#
#     uvicorn automation.main:app
#
app = create_app()