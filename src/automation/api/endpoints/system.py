"""System management API endpoints."""

from __future__ import annotations

import imaplib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from automation.api.dependencies import get_settings
from automation.config.settings import Settings

router = APIRouter()


class SystemStatsResponse(BaseModel):
    total_emails_processed: int
    files_in_safe_storage: int
    files_in_quarantine: int
    last_processing_time: datetime | None
    system_status: str


class ConfigResponse(BaseModel):
    imap_host: str
    imap_mailbox: str
    max_file_size_mb: int
    allowed_extensions: list[str]
    scan_interval_minutes: int


class TestConnectionRequest(BaseModel):
    imap_host: str | None = None
    imap_port: int | None = None
    imap_username: str | None = None
    imap_password: str | None = None
    imap_mailbox: str | None = None


@router.get("/system/stats", response_model=SystemStatsResponse)
async def get_system_stats(settings: Settings = Depends(get_settings)):
    """Return high-level system counters."""
    safe_path = Path(settings.safe_storage_dir)
    quarantine_path = Path(settings.quarantine_dir)

    safe_files = len(list(safe_path.glob("*"))) if safe_path.exists() else 0
    quarantine_files = len(list(quarantine_path.glob("*"))) if quarantine_path.exists() else 0

    return SystemStatsResponse(
        total_emails_processed=0,
        files_in_safe_storage=safe_files,
        files_in_quarantine=quarantine_files,
        last_processing_time=None,
        system_status="healthy",
    )


@router.get("/system/config", response_model=ConfigResponse)
async def get_system_config(settings: Settings = Depends(get_settings)):
    """Return effective runtime configuration used by the app."""
    return ConfigResponse(
        imap_host=settings.imap_host,
        imap_mailbox=settings.imap_mailbox,
        max_file_size_mb=settings.max_file_size_mb,
        allowed_extensions=settings.allowed_file_extensions,
        scan_interval_minutes=settings.scan_interval_minutes,
    )


@router.post("/system/test-connection")
async def test_imap_connection(
    request: TestConnectionRequest | None = None,
    settings: Settings = Depends(get_settings),
):
    """Test IMAP connectivity using request data or configured defaults."""
    try:
        req = request or TestConnectionRequest()
        host = req.imap_host or settings.imap_host
        port = req.imap_port or settings.imap_port
        username = req.imap_username or settings.imap_user
        password = req.imap_password or settings.imap_password
        mailbox = req.imap_mailbox or settings.imap_mailbox

        if not host or not username or not password:
            return {
                "success": False,
                "status": "failed",
                "error": "IMAP credentials not provided",
            }

        with imaplib.IMAP4_SSL(host, port) as imap:
            imap.login(username, password)
            status, _ = imap.select(mailbox)
            if status != "OK":
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Failed to select mailbox '{mailbox}'",
                }

        return {
            "success": True,
            "status": "success",
            "message": f"IMAP connection successful. Mailbox '{mailbox}' found.",
            "server": host,
        }
    except imaplib.IMAP4.error as exc:
        return {
            "success": False,
            "status": "failed",
            "error": f"IMAP auth failed: {str(exc)}",
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "failed",
            "error": f"IMAP connection failed: {str(exc)}",
        }
