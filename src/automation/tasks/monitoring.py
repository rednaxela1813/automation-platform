"""Background monitoring tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import psutil

from automation.celery_app import celery_app
from automation.config.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task
def system_health_check_task() -> Dict[str, Any]:
    """Run a basic health check for system resources and integrations."""
    try:
        logger.info("Starting system health check")

        health_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {},
        }

        health_status["checks"]["disk_space"] = _check_disk_space()
        health_status["checks"]["memory"] = _check_memory_usage()
        health_status["checks"]["processes"] = _check_processes()
        health_status["checks"]["directories"] = _check_storage_directories()
        health_status["checks"]["imap"] = _check_imap_connection()

        failed_checks = [
            check for check in health_status["checks"].values() if check["status"] == "error"
        ]

        if failed_checks:
            health_status["overall_status"] = "unhealthy"
            logger.warning(f"System health check found {len(failed_checks)} issues")
        else:
            logger.info("System health check passed")

        return health_status

    except Exception as exc:
        logger.error(f"System health check failed: {exc}", exc_info=True)
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "error",
            "error": str(exc),
        }


def _check_disk_space() -> Dict[str, Any]:
    """Check root disk availability."""
    try:
        disk_usage = psutil.disk_usage("/")
        free_percent = (disk_usage.free / disk_usage.total) * 100

        status = "ok"
        if free_percent < 5:
            status = "error"
        elif free_percent < 10:
            status = "warning"

        return {
            "status": status,
            "free_space_gb": round(disk_usage.free / (1024**3), 2),
            "total_space_gb": round(disk_usage.total / (1024**3), 2),
            "free_percent": round(free_percent, 2),
            "message": f"Free: {free_percent:.1f}% ({disk_usage.free / (1024**3):.2f} GB)",
        }

    except Exception as exc:
        return {"status": "error", "message": f"Disk check failed: {exc}"}


def _check_memory_usage() -> Dict[str, Any]:
    """Check memory pressure."""
    try:
        memory = psutil.virtual_memory()
        used_percent = memory.percent

        status = "ok"
        if used_percent > 90:
            status = "error"
        elif used_percent > 80:
            status = "warning"

        return {
            "status": status,
            "used_percent": used_percent,
            "available_gb": round(memory.available / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2),
            "message": f"Memory usage: {used_percent:.1f}%",
        }

    except Exception as exc:
        return {"status": "error", "message": f"Memory check failed: {exc}"}


def _check_processes() -> Dict[str, Any]:
    """Check whether expected Python/Celery processes are running."""
    try:
        process_names = ["python", "celery"]
        running_processes = []

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                if any(token in name for token in process_names):
                    cmdline = proc.info.get("cmdline") or []
                    running_processes.append(
                        {
                            "pid": proc.info.get("pid"),
                            "name": proc.info.get("name"),
                            "cmdline": " ".join(cmdline[:3]) if cmdline else "",
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "status": "ok",
            "running_processes": len(running_processes),
            "processes": running_processes[:5],  # Keep payload compact.
            "message": f"Found {len(running_processes)} relevant processes",
        }

    except Exception as exc:
        return {"status": "error", "message": f"Process check failed: {exc}"}


def _check_storage_directories() -> Dict[str, Any]:
    """Check existence and basic health of storage/log directories."""
    try:
        directories_to_check = [
            Path(settings.safe_storage_dir),
            Path(settings.quarantine_dir),
            Path("logs"),
        ]

        directory_status = {}

        for directory in directories_to_check:
            if directory.exists():
                files = list(directory.glob("**/*"))
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                directory_status[str(directory)] = {
                    "exists": True,
                    "files_count": len([f for f in files if f.is_file()]),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "writable": directory.stat().st_mode & 0o200 != 0,
                }
            else:
                directory_status[str(directory)] = {
                    "exists": False,
                    "files_count": 0,
                    "total_size_mb": 0,
                    "writable": False,
                }

        all_ok = all(info["exists"] and info["writable"] for info in directory_status.values())

        return {
            "status": "ok" if all_ok else "warning",
            "directories": directory_status,
            "message": "All directories accessible" if all_ok else "Some directories have issues",
        }

    except Exception as exc:
        return {"status": "error", "message": f"Directory check failed: {exc}"}


def _check_imap_connection() -> Dict[str, Any]:
    """Check IMAP connectivity by attempting message fetch."""
    try:
        from automation.adapters.email_imap import ImapEmailClient

        client = ImapEmailClient()
        messages = client.fetch_new_messages()

        return {
            "status": "ok",
            "host": client.host,
            "mailbox": client.mailbox,
            "unread_messages": len(messages),
            "message": f"IMAP connection OK, {len(messages)} unread messages",
        }

    except Exception as exc:
        return {"status": "error", "message": f"IMAP connection failed: {exc}"}


@celery_app.task
def generate_daily_metrics_task() -> Dict[str, Any]:
    """Generate simple daily operational metrics."""
    try:
        logger.info("Generating daily metrics")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        metrics = {"date": start_date.date().isoformat(), "period": "24h", "metrics": {}}

        safe_storage_dir = Path(settings.safe_storage_dir)
        files_processed = len(
            [
                f
                for f in safe_storage_dir.glob("**/*")
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) >= start_date
            ]
        )

        quarantine_dir = Path(settings.quarantine_dir)
        files_quarantined = len(
            [
                f
                for f in quarantine_dir.glob("**/*")
                if f.is_file() and datetime.fromtimestamp(f.stat().st_mtime) >= start_date
            ]
        )

        total_files = files_processed + files_quarantined
        quarantine_rate = (
            round((files_quarantined / total_files) * 100, 2) if total_files > 0 else 0
        )

        metrics["metrics"] = {
            "files_processed": files_processed,
            "files_quarantined": files_quarantined,
            "processing_rate": round(files_processed / 24, 2),  # files/hour
            "quarantine_rate": quarantine_rate,
        }

        logger.info(f"Daily metrics generated: {metrics['metrics']}")
        return {"status": "success", "metrics": metrics}

    except Exception as exc:
        logger.error(f"Daily metrics generation failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}


@celery_app.task
def alert_on_errors_task(threshold: int = 5) -> Dict[str, Any]:
    """Alert when error count in logs exceeds threshold for the last hour."""
    try:
        log_file = Path(settings.log_dir) / "automation.log"

        if not log_file.exists():
            return {"status": "ok", "message": "No log file found"}

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        error_count = 0

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if "ERROR" in line:
                    try:
                        log_time_str = line.split(" - ")[0]
                        log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S")
                        if start_time <= log_time <= end_time:
                            error_count += 1
                    except (ValueError, IndexError):
                        continue

        if error_count >= threshold:
            # Placeholder for real alert channel (email/Slack/etc.)
            logger.warning(f"Error threshold exceeded: {error_count} errors in last hour")
            return {
                "status": "alert_sent",
                "error_count": error_count,
                "threshold": threshold,
                "period": "1 hour",
            }

        return {
            "status": "ok",
            "error_count": error_count,
            "message": f"Error count ({error_count}) below threshold ({threshold})",
        }

    except Exception as exc:
        logger.error(f"Error alerting task failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}
