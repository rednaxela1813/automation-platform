# autmation-platform/src/automation/api/dependencies.py

"""FastAPI dependency providers for application services."""

from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from automation.adapters.email_imap import ImapEmailClient
from automation.adapters.file_storage import LocalFileStorage
from automation.adapters.parser_registry import get_document_parsers
from automation.config.settings import Settings


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    from automation.config.settings import settings

    return settings


async def get_email_processor() -> ImapEmailClient:
    """Provide email processor dependency."""
    return ImapEmailClient()


async def get_file_storage() -> LocalFileStorage:
    """Provide local file storage dependency."""
    return LocalFileStorage()


async def get_document_parser():
    """Provide parser list dependency in priority order."""
    return get_document_parsers()


async def verify_api_key(api_key: str | None = None):
    """Validate API key when one is configured."""
    settings = get_settings()

    if not settings.api_key:
        return True

    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True
