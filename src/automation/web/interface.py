"""Web interface routes for Email Automation Platform."""

from __future__ import annotations

import imaplib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from automation.config.settings import settings

templates = Jinja2Templates(directory="templates")
web_router = APIRouter()
logger = logging.getLogger(__name__)


class WebStats(BaseModel):
    """Summary statistics for dashboard widgets."""

    total_emails_processed: int = 0
    files_in_safe_storage: int = 0
    files_in_quarantine: int = 0
    system_status: str = "Unknown"
    last_processing_time: Optional[datetime] = None


class FileInfo(BaseModel):
    """View model for file list rendering."""

    filename: str
    filepath: str
    size: int
    size_formatted: str
    created_at: str


class QuarantineFileInfo(BaseModel):
    """View model for quarantine file list rendering."""

    filename: str
    size: int
    size_formatted: str
    created_at: str
    quarantine_reason: str


def get_web_stats() -> WebStats:
    """Calculate top-level dashboard statistics."""
    try:
        safe_storage = Path(settings.safe_storage_dir)
        quarantine_storage = Path(settings.quarantine_dir)

        allowed_extensions = {ext.lower() for ext in settings.allowed_file_extensions}

        def is_safe_file(path: Path) -> bool:
            return path.is_file() and path.suffix.lower() in allowed_extensions

        def is_quarantine_file(path: Path) -> bool:
            return path.is_file() and not path.name.endswith(".quarantine_info.json")

        safe_files = (
            len([f for f in safe_storage.iterdir() if is_safe_file(f)])
            if safe_storage.exists()
            else 0
        )
        quarantine_files = (
            len([f for f in quarantine_storage.iterdir() if is_quarantine_file(f)])
            if quarantine_storage.exists()
            else 0
        )

        return WebStats(
            total_emails_processed=safe_files + quarantine_files,
            files_in_safe_storage=safe_files,
            files_in_quarantine=quarantine_files,
            system_status="Active" if safe_files > 0 else "Ready",
            last_processing_time=datetime.now() if safe_files > 0 else None,
        )
    except Exception as exc:
        logger.exception("Error getting web stats: %s", exc)
        return WebStats()


def get_recent_files(limit: int = 5) -> List[FileInfo]:
    """Return latest files from safe storage."""
    files: List[FileInfo] = []
    try:
        safe_storage = Path(settings.safe_storage_dir)
        if not safe_storage.exists():
            return files

        allowed_extensions = {ext.lower() for ext in settings.allowed_file_extensions}
        all_files = [
            f
            for f in safe_storage.iterdir()
            if f.is_file() and f.suffix.lower() in allowed_extensions
        ]
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for file_path in all_files[:limit]:
            stat = file_path.stat()
            size_mb = stat.st_size / 1024 / 1024

            try:
                relative_path = file_path.relative_to(safe_storage.parent)
            except ValueError:
                relative_path = file_path

            size_formatted = f"{size_mb:.1f} MB" if size_mb > 1 else f"{stat.st_size // 1024} KB"
            created_at = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
            files.append(
                FileInfo(
                    filename=file_path.name,
                    filepath=str(relative_path),
                    size=stat.st_size,
                    size_formatted=size_formatted,
                    created_at=created_at,
                )
            )

    except Exception as exc:
        logger.exception("Error getting recent files: %s", exc)

    return files


def get_recent_quarantine_files(limit: int = 5) -> List[QuarantineFileInfo]:
    """Return latest files from quarantine storage."""
    files: List[QuarantineFileInfo] = []
    try:
        quarantine_storage = Path(settings.quarantine_dir)
        if not quarantine_storage.exists():
            return files

        all_files = [
            f
            for f in quarantine_storage.iterdir()
            if f.is_file() and not f.name.endswith(".quarantine_info.json")
        ]
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for file_path in all_files[:limit]:
            stat = file_path.stat()
            size_mb = stat.st_size / 1024 / 1024
            size_formatted = f"{size_mb:.1f} MB" if size_mb > 1 else f"{stat.st_size // 1024} KB"
            created_at = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")

            quarantine_reason = "Unknown"
            info_path = file_path.with_suffix(".quarantine_info.json")
            if info_path.exists():
                try:
                    with open(info_path, "r", encoding="utf-8") as fh:
                        info = json.load(fh)
                    quarantine_reason = info.get("quarantine_reason", quarantine_reason)
                except (OSError, ValueError):
                    pass

            files.append(
                QuarantineFileInfo(
                    filename=file_path.name,
                    size=stat.st_size,
                    size_formatted=size_formatted,
                    created_at=created_at,
                    quarantine_reason=quarantine_reason,
                )
            )
    except Exception as exc:
        logger.exception("Error getting recent quarantine files: %s", exc)

    return files


@web_router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render dashboard page."""
    stats = get_web_stats()
    config = {
        "imap_host": settings.imap_host,
        "imap_port": settings.imap_port,
        "imap_mailbox": settings.imap_mailbox,
        "max_file_size_mb": settings.max_file_size_mb,
        "allowed_extensions": [ext.lstrip(".") for ext in settings.allowed_file_extensions],
    }
    recent_files = get_recent_files(5)
    quarantine_files = get_recent_quarantine_files(5)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Dashboard",
            "current_page": "dashboard",
            "stats": stats.dict(),
            "config": config,
            "recent_files": recent_files,
            "quarantine_files": quarantine_files,
        },
    )


@web_router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render settings page."""
    config = {
        "imap_host": settings.imap_host,
        "imap_port": settings.imap_port,
        "imap_username": settings.imap_user,
        "imap_mailbox": settings.imap_mailbox,
        "max_file_size_mb": settings.max_file_size_mb,
        "allowed_extensions": [ext.lstrip(".") for ext in settings.allowed_file_extensions],
        "storage_path": str(Path(settings.safe_storage_dir).parent),
        "scan_interval_minutes": settings.scan_interval_minutes,
        "auto_processing": False,
        "enable_quarantine": True,
    }

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings",
            "current_page": "settings",
            "config": config,
        },
    )


@web_router.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """Render files page."""
    all_files = get_recent_files(settings.default_page_limit)
    pdf_count = sum(1 for f in all_files if f.filename.lower().endswith(".pdf"))

    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "title": "Files",
            "current_page": "files",
            "files": all_files,
            "pdf_count": pdf_count,
        },
    )


@web_router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Render logs page with sample log records."""
    now = datetime.now()
    logs = [
        {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "Email processing completed: 4 messages processed",
        },
        {
            "timestamp": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "SUCCESS",
            "message": "PDF file extracted: Novaglen_481474921.pdf (53KB)",
        },
        {
            "timestamp": (now - timedelta(minutes=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "SUCCESS",
            "message": "PDF file extracted: Eyelashes_and_Beauty_481483348.pdf (52KB)",
        },
        {
            "timestamp": (now - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"),
            "level": "INFO",
            "message": "IMAP connection established to mail.deilmann.sk",
        },
    ]

    log_stats = {
        "ERROR": sum(1 for log in logs if log.get("level") == "ERROR"),
        "WARNING": sum(1 for log in logs if log.get("level") == "WARNING"),
        "SUCCESS": sum(1 for log in logs if log.get("level") == "SUCCESS"),
        "INFO": sum(1 for log in logs if log.get("level") == "INFO"),
    }

    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "title": "System Logs",
            "current_page": "logs",
            "logs": logs,
            "log_stats": log_stats,
        },
    )


# Web API endpoints
@web_router.get("/api/web/stats")
async def web_stats():
    """Return dashboard statistics as JSON."""
    return get_web_stats().dict()


@web_router.post("/api/web/test-connection")
async def test_connection_web(
    imap_host: str = Form(...),
    imap_port: int = Form(...),
    imap_username: str = Form(...),
    imap_mailbox: str = Form(...),
    imap_password: str | None = Form(None),
):
    """Test IMAP connection with provided form values."""
    try:
        host = imap_host or settings.imap_host
        port = imap_port or settings.imap_port
        username = imap_username or settings.imap_user
        password = imap_password or settings.imap_password
        mailbox = imap_mailbox or settings.imap_mailbox

        if not host or not username or not password:
            return {"success": False, "error": "IMAP credentials not provided"}

        with imaplib.IMAP4_SSL(host, port) as imap:
            imap.login(username, password)
            status, _ = imap.select(mailbox)
            if status != "OK":
                return {"success": False, "error": f"Failed to select mailbox '{mailbox}'"}

        return {
            "success": True,
            "message": f"Connection to {host}:{port} succeeded. Mailbox '{mailbox}' is available.",
        }
    except imaplib.IMAP4.error as exc:
        return {"success": False, "error": f"IMAP auth failed: {str(exc)}"}
    except Exception as exc:
        return {"success": False, "error": f"Connection test failed: {str(exc)}"}


@web_router.get("/api/web/connection-status")
async def connection_status_web():
    """Return coarse connection status based on configured IMAP credentials."""
    try:
        if settings.imap_host and settings.imap_user:
            return {"connected": True, "last_check": datetime.now().strftime("%H:%M:%S")}
        return {"connected": False, "error": "Connection settings are incomplete"}
    except Exception as exc:
        return {"connected": False, "error": str(exc)}
