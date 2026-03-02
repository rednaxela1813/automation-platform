# automation-platform/src/automation/tasks/file_cleanup.py

"""
Background tasks for file cleanup
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from automation.celery_app import celery_app
from automation.config.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_files_task(days_old: int | None = None) -> Dict[str, Any]:
    """
    Task for cleaning old files from storage

    Args:
        days_old: File age in days for deletion
    """
    try:
        effective_days_old = days_old if days_old is not None else settings.cleanup_days_old
        logger.info(f"Starting file cleanup for files older than {effective_days_old} days")

        cutoff_date = datetime.now() - timedelta(days=effective_days_old)

        # Clean safe storage
        safe_storage_dir = Path(settings.safe_storage_dir)
        cleaned_safe = _cleanup_directory(safe_storage_dir, cutoff_date)

        # Clean quarantine with configured retention period.
        quarantine_dir = Path(settings.quarantine_dir)
        quarantine_cutoff = datetime.now() - timedelta(days=settings.quarantine_days_old)
        cleaned_quarantine = _cleanup_directory(quarantine_dir, quarantine_cutoff)

        # Clean logs with configured retention period.
        logs_dir = Path(settings.log_dir)
        if logs_dir.exists():
            logs_cutoff = datetime.now() - timedelta(days=settings.logs_retention_days)
            cleaned_logs = _cleanup_directory(logs_dir, logs_cutoff, "*.log.*")
        else:
            cleaned_logs = {"files_removed": 0, "space_freed": 0}

        total_files = (
            cleaned_safe["files_removed"]
            + cleaned_quarantine["files_removed"]
            + cleaned_logs["files_removed"]
        )

        total_space = (
            cleaned_safe["space_freed"]
            + cleaned_quarantine["space_freed"]
            + cleaned_logs["space_freed"]
        )

        logger.info(
            f"Cleanup completed: {total_files} files removed, "
            f"{total_space / (1024 * 1024):.2f} MB freed"
        )

        return {
            "status": "success",
            "files_removed": total_files,
            "space_freed_mb": round(total_space / (1024 * 1024), 2),
            "safe_storage": cleaned_safe,
            "quarantine": cleaned_quarantine,
            "logs": cleaned_logs,
        }

    except Exception as exc:
        logger.error(f"File cleanup failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}


def _cleanup_directory(
    directory: Path, cutoff_date: datetime, pattern: str = "*"
) -> Dict[str, Any]:
    """
    Clean files in directory older than cutoff_date

    Args:
        directory: Directory to clean
        cutoff_date: Date threshold for deletion
        pattern: File search pattern

    Returns:
        Cleanup statistics
    """
    if not directory.exists():
        return {"files_removed": 0, "space_freed": 0, "errors": []}

    files_removed = 0
    space_freed = 0
    errors = []

    try:
        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            # Check file age
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

            if file_mtime < cutoff_date:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()

                    files_removed += 1
                    space_freed += file_size

                    logger.debug(f"Removed old file: {file_path}")

                except OSError as e:
                    error_msg = f"Failed to delete {file_path}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)

    except Exception as e:
        errors.append(f"Directory cleanup error: {e}")
        logger.error(f"Directory cleanup error: {e}")

    return {"files_removed": files_removed, "space_freed": space_freed, "errors": errors}


@celery_app.task
def cleanup_quarantine_task() -> Dict[str, Any]:
    """
    Special task for quarantine cleanup
    Deletes files older than configured quarantine retention period.
    """
    try:
        logger.info("Starting quarantine cleanup")

        quarantine_dir = Path(settings.quarantine_dir)
        cutoff_date = datetime.now() - timedelta(days=settings.quarantine_days_old)

        result = _cleanup_directory(quarantine_dir, cutoff_date)

        logger.info(f"Quarantine cleanup completed: {result['files_removed']} files removed")

        return {"status": "success", **result}

    except Exception as exc:
        logger.error(f"Quarantine cleanup failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}


@celery_app.task
def archive_processed_files_task(archive_days: int | None = None) -> Dict[str, Any]:
    """
    Archive processed files older than archive_days days
    """
    try:
        effective_archive_days = (
            archive_days if archive_days is not None else settings.archive_days_old
        )
        logger.info(
            f"Starting file archiving for files older than {effective_archive_days} days"
        )

        safe_storage_dir = Path(settings.safe_storage_dir)
        archive_dir = safe_storage_dir.parent / "archive"
        archive_dir.mkdir(exist_ok=True)

        cutoff_date = datetime.now() - timedelta(days=effective_archive_days)

        files_archived = 0

        for file_path in safe_storage_dir.glob("*"):
            if not file_path.is_file():
                continue

            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

            if file_mtime < cutoff_date:
                # Create archive structure by year and month
                archive_subdir = archive_dir / str(file_mtime.year) / f"{file_mtime.month:02d}"
                archive_subdir.mkdir(parents=True, exist_ok=True)

                # Move file to archive
                archive_path = archive_subdir / file_path.name
                file_path.rename(archive_path)

                files_archived += 1

        logger.info(f"File archiving completed: {files_archived} files archived")

        return {
            "status": "success",
            "files_archived": files_archived,
            "archive_location": str(archive_dir),
        }

    except Exception as exc:
        logger.error(f"File archiving failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}
