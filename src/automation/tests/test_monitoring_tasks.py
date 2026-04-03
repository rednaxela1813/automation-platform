from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import automation.tasks.monitoring as tasks


def test_check_disk_space_warning(monkeypatch):
    monkeypatch.setattr(
        tasks.psutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=100, free=8),
    )

    result = tasks._check_disk_space()

    assert result["status"] == "warning"
    assert result["free_percent"] == 8.0


def test_check_memory_usage_error(monkeypatch):
    monkeypatch.setattr(
        tasks.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(percent=95, available=2 * 1024**3, total=8 * 1024**3),
    )

    result = tasks._check_memory_usage()

    assert result["status"] == "error"
    assert result["used_percent"] == 95


def test_check_processes_collects_python_and_celery(monkeypatch):
    process_list = [
        SimpleNamespace(info={"pid": 1, "name": "Python", "cmdline": ["python", "run.py"]}),
        SimpleNamespace(info={"pid": 2, "name": "celery", "cmdline": ["celery", "-A", "app"]}),
        SimpleNamespace(info={"pid": 3, "name": "nginx", "cmdline": ["nginx"]}),
    ]
    monkeypatch.setattr(tasks.psutil, "process_iter", lambda attrs: iter(process_list))

    result = tasks._check_processes()

    assert result["status"] == "ok"
    assert result["running_processes"] == 2
    assert len(result["processes"]) == 2


def test_check_storage_directories_reports_warning_for_missing_dir(tmp_path: Path, monkeypatch):
    safe_dir = tmp_path / "safe"
    quarantine_dir = tmp_path / "quarantine"
    logs_dir = tmp_path / "logs"
    safe_dir.mkdir()
    quarantine_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "safe_storage_dir", str(safe_dir))
    monkeypatch.setattr(tasks.settings, "quarantine_dir", str(quarantine_dir))
    monkeypatch.chdir(tmp_path)

    result = tasks._check_storage_directories()

    assert result["status"] == "warning"
    assert result["directories"]["logs"]["exists"] is False


def test_check_imap_connection_returns_error_on_exception(monkeypatch):
    class DummyClient:
        def __init__(self):
            raise RuntimeError("imap down")

    monkeypatch.setattr("automation.adapters.email_imap.ImapEmailClient", DummyClient)

    result = tasks._check_imap_connection()

    assert result["status"] == "error"
    assert "imap down" in result["message"]


def test_system_health_check_task_marks_unhealthy_when_one_check_fails(monkeypatch):
    monkeypatch.setattr(tasks, "_check_disk_space", lambda: {"status": "ok"})
    monkeypatch.setattr(tasks, "_check_memory_usage", lambda: {"status": "ok"})
    monkeypatch.setattr(tasks, "_check_processes", lambda: {"status": "ok"})
    monkeypatch.setattr(tasks, "_check_storage_directories", lambda: {"status": "warning"})
    monkeypatch.setattr(tasks, "_check_imap_connection", lambda: {"status": "error"})

    payload = tasks.system_health_check_task.run()

    assert payload["overall_status"] == "unhealthy"
    assert payload["checks"]["imap"]["status"] == "error"


def test_generate_daily_metrics_task_counts_recent_files(tmp_path: Path, monkeypatch):
    safe_dir = tmp_path / "safe"
    quarantine_dir = tmp_path / "quarantine"
    safe_dir.mkdir()
    quarantine_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "safe_storage_dir", str(safe_dir))
    monkeypatch.setattr(tasks.settings, "quarantine_dir", str(quarantine_dir))

    processed = safe_dir / "invoice.pdf"
    processed.write_text("x", encoding="utf-8")
    quarantined = quarantine_dir / "bad.exe"
    quarantined.write_text("y", encoding="utf-8")

    old_file = safe_dir / "old.pdf"
    old_file.write_text("old", encoding="utf-8")

    old_ts = (datetime.now() - timedelta(days=2)).timestamp()
    import os
    os.utime(old_file, (old_ts, old_ts))

    payload = tasks.generate_daily_metrics_task.run()

    assert payload["status"] == "success"
    assert payload["metrics"]["metrics"]["files_processed"] == 1
    assert payload["metrics"]["metrics"]["files_quarantined"] == 1
    assert payload["metrics"]["metrics"]["quarantine_rate"] == 50.0


def test_alert_on_errors_task_returns_alert_sent(tmp_path: Path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "log_dir", str(log_dir))

    now = datetime.now()
    recent = now.strftime("%Y-%m-%d %H:%M:%S")
    old = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    log_file = log_dir / "automation.log"
    log_file.write_text(
        f"{recent} - automation - ERROR - boom\n"
        f"{recent} - automation - ERROR - bang\n"
        f"{old} - automation - ERROR - stale\n",
        encoding="utf-8",
    )

    payload = tasks.alert_on_errors_task.run(threshold=2)

    assert payload == {
        "status": "alert_sent",
        "error_count": 2,
        "threshold": 2,
        "period": "1 hour",
    }


def test_alert_on_errors_task_returns_ok_when_log_missing(tmp_path: Path, monkeypatch):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "log_dir", str(log_dir))

    payload = tasks.alert_on_errors_task.run()

    assert payload == {"status": "ok", "message": "No log file found"}
