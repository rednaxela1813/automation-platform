"""File management API endpoints."""

from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from automation.api.dependencies import get_settings
from automation.config.settings import Settings

router = APIRouter()


def _resolve_safe_file(path_value: str, settings: Settings) -> Path:
    safe_dir = Path(settings.safe_storage_dir).resolve()
    storage_root = safe_dir.parent.resolve()

    decoded = unquote(path_value or "").lstrip("/")
    if not decoded:
        raise HTTPException(status_code=404, detail="File not found")

    # Primary: "safe/filename.ext" relative to storage root.
    candidate = (storage_root / decoded).resolve()
    if candidate.is_file() and candidate.is_relative_to(safe_dir):
        return candidate

    # Fallback: path relative to safe dir.
    candidate = (safe_dir / decoded).resolve()
    if candidate.is_file() and candidate.is_relative_to(safe_dir):
        return candidate

    raise HTTPException(status_code=404, detail="File not found")


def _resolve_quarantine_file(filename: str, settings: Settings) -> Path:
    quarantine_dir = Path(settings.quarantine_dir).resolve()
    decoded = unquote(filename or "")
    if not decoded:
        raise HTTPException(status_code=404, detail="File not found in quarantine")

    candidate = (quarantine_dir / decoded).resolve()
    if not candidate.is_relative_to(quarantine_dir):
        raise HTTPException(status_code=404, detail="File not found in quarantine")
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="File not found in quarantine")
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail="Invalid file")
    return candidate


def _is_quarantine_payload_file(path: Path) -> bool:
    return path.is_file() and not path.name.endswith(".quarantine_info.json")


def _load_quarantine_reason(file_path: Path) -> str:
    info_path = file_path.with_suffix(".quarantine_info.json")
    if not info_path.exists() or not info_path.is_file():
        return "Unknown"

    try:
        with open(info_path, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        return str(info.get("quarantine_reason") or "Unknown")
    except (OSError, ValueError, TypeError):
        return "Unknown"


@router.get("/files/safe")
async def list_safe_files(
    limit: int | None = None,
    offset: int = 0,
    settings: Settings = Depends(get_settings),
):
    """List files from safe storage with pagination."""
    page_limit = limit if limit is not None else settings.default_page_limit
    safe_dir = Path(settings.safe_storage_dir)
    if not safe_dir.exists():
        return {"files": [], "total": 0}

    files = list(safe_dir.glob("*"))[offset : offset + page_limit]

    file_info = []
    for file in files:
        if file.is_file():
            stat = file.stat()
            file_info.append(
                {
                    "name": file.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime),
                }
            )

    return {"files": file_info, "total": len(list(safe_dir.glob("*")))}


@router.get("/files/view/{path_value:path}")
async def view_safe_file(path_value: str, settings: Settings = Depends(get_settings)):
    """Open file inline in browser when MIME allows it."""
    file_path = _resolve_safe_file(path_value, settings)
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=media_type or "application/octet-stream",
        filename=file_path.name,
        headers={"Content-Disposition": f'inline; filename="{file_path.name}"'},
    )


@router.get("/files/download")
async def download_safe_file(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings),
):
    """Download one file from safe storage."""
    file_path = _resolve_safe_file(path, settings)
    media_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(
        path=str(file_path),
        media_type=media_type or "application/octet-stream",
        filename=file_path.name,
    )


@router.get("/files/info")
async def file_info(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings),
):
    """Return metadata for one file in safe storage."""
    file_path = _resolve_safe_file(path, settings)
    stat = file_path.stat()
    size_kb = stat.st_size / 1024
    size_formatted = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
    mime_type, _ = mimetypes.guess_type(str(file_path))

    return {
        "success": True,
        "filename": file_path.name,
        "size": stat.st_size,
        "size_formatted": size_formatted,
        "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M"),
        "mime_type": mime_type,
        "extracted_data": None,
    }


@router.get("/files/parsed")
async def get_parsed_file_data(
    path: str = Query(..., description="Relative path to source file in safe storage"),
    settings: Settings = Depends(get_settings),
):
    """Return parsed JSON payload generated for a concrete source file."""
    source_file_path = _resolve_safe_file(path, settings)
    parsed_file_path = source_file_path.with_suffix(".parsed.json")

    if not parsed_file_path.exists() or not parsed_file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Parsed JSON is not available for file '{source_file_path.name}'",
        )

    try:
        with open(parsed_file_path, "r", encoding="utf-8") as fh:
            parsed_payload = json.load(fh)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read parsed JSON: {str(exc)}")

    return {
        "success": True,
        "source_file": source_file_path.name,
        "parsed_file": parsed_file_path.name,
        "data": parsed_payload,
    }


@router.get("/files/analyze")
async def analyze_file(
    path: str = Query(..., description="Relative path to safe storage file"),
    settings: Settings = Depends(get_settings),
):
    """Placeholder endpoint for file analysis details."""
    _resolve_safe_file(path, settings)
    return PlainTextResponse("Analyze is not implemented yet.", status_code=501)


@router.post("/files/cleanup")
async def cleanup_old_files(settings: Settings = Depends(get_settings)):
    """Delete files from safe storage older than configured retention period."""
    safe_dir = Path(settings.safe_storage_dir)
    if not safe_dir.exists():
        return {"message": "Safe storage directory not found", "files_removed": 0}

    cutoff = datetime.now() - timedelta(days=settings.cleanup_days_old)
    removed = 0
    for file_path in safe_dir.iterdir():
        if not file_path.is_file():
            continue
        if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff:
            try:
                file_path.unlink()
                removed += 1
            except OSError:
                continue

    return {"message": f"Removed {removed} files", "files_removed": removed}


@router.get("/files/quarantine")
async def list_quarantine_files(
    limit: int | None = None,
    offset: int = 0,
    settings: Settings = Depends(get_settings),
):
    """List quarantine files with pagination."""
    page_limit = limit if limit is not None else settings.default_page_limit
    quarantine_dir = Path(settings.quarantine_dir)
    if not quarantine_dir.exists():
        return {"files": [], "total": 0}

    quarantine_files = [f for f in quarantine_dir.glob("*") if _is_quarantine_payload_file(f)]
    files = quarantine_files[offset : offset + page_limit]

    file_info = []
    for file in files:
        stat = file.stat()
        file_info.append(
            {
                "name": file.name,
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
                "quarantine_reason": _load_quarantine_reason(file),
            }
        )

    return {"files": file_info, "total": len(quarantine_files)}


@router.delete("/files/quarantine/{filename}")
async def delete_quarantine_file(filename: str, settings: Settings = Depends(get_settings)):
    """Delete one file from quarantine."""
    file_path = _resolve_quarantine_file(filename, settings)

    try:
        info_path = file_path.with_suffix(".quarantine_info.json")
        file_path.unlink()
        if info_path.exists() and info_path.is_file():
            info_path.unlink()
        return {"message": f"File {filename} deleted from quarantine"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(exc)}")
