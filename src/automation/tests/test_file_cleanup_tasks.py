from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import automation.tasks.file_cleanup as tasks


def test_cleanup_directory_removes_only_old_matching_files(tmp_path: Path):
    old_file = tmp_path / "old.txt"
    old_file.write_text("old", encoding="utf-8")
    recent_file = tmp_path / "recent.txt"
    recent_file.write_text("recent", encoding="utf-8")
    ignored_file = tmp_path / "ignored.log"
    ignored_file.write_text("ignored", encoding="utf-8")

    old_ts = (datetime.now() - timedelta(days=10)).timestamp()
    recent_ts = datetime.now().timestamp()
    old_file.touch()
    recent_file.touch()
    ignored_file.touch()
    import os
    os.utime(old_file, (old_ts, old_ts))
    os.utime(recent_file, (recent_ts, recent_ts))
    os.utime(ignored_file, (old_ts, old_ts))

    result = tasks._cleanup_directory(tmp_path, datetime.now() - timedelta(days=5), "*.txt")

    assert result["files_removed"] == 1
    assert result["space_freed"] == 3
    assert result["errors"] == []
    assert not old_file.exists()
    assert recent_file.exists()
    assert ignored_file.exists()


def test_cleanup_old_files_task_aggregates_safe_quarantine_and_logs(tmp_path: Path, monkeypatch):
    safe_dir = tmp_path / "safe"
    quarantine_dir = tmp_path / "quarantine"
    logs_dir = tmp_path / "logs"
    safe_dir.mkdir()
    quarantine_dir.mkdir()
    logs_dir.mkdir()

    monkeypatch.setattr(tasks.settings, "safe_storage_dir", str(safe_dir))
    monkeypatch.setattr(tasks.settings, "quarantine_dir", str(quarantine_dir))
    monkeypatch.setattr(tasks.settings, "log_dir", str(logs_dir))
    monkeypatch.setattr(tasks.settings, "cleanup_days_old", 30)
    monkeypatch.setattr(tasks.settings, "quarantine_days_old", 7)
    monkeypatch.setattr(tasks.settings, "logs_retention_days", 14)

    calls = []

    def fake_cleanup(directory, cutoff_date, pattern="*"):
        calls.append((directory, pattern))
        name = directory.name
        if name == "safe":
            return {"files_removed": 2, "space_freed": 1024, "errors": []}
        if name == "quarantine":
            return {"files_removed": 1, "space_freed": 2048, "errors": []}
        return {"files_removed": 3, "space_freed": 512, "errors": []}

    monkeypatch.setattr(tasks, "_cleanup_directory", fake_cleanup)

    payload = tasks.cleanup_old_files_task.run()

    assert payload["status"] == "success"
    assert payload["files_removed"] == 6
    assert payload["space_freed_mb"] == 0.0
    assert [pattern for _, pattern in calls] == ["*", "*", "*.log.*"]


def test_cleanup_quarantine_task_returns_directory_cleanup_result(monkeypatch, tmp_path: Path):
    quarantine_dir = tmp_path / "quarantine"
    quarantine_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "quarantine_dir", str(quarantine_dir))
    monkeypatch.setattr(tasks.settings, "quarantine_days_old", 7)
    monkeypatch.setattr(
        tasks,
        "_cleanup_directory",
        lambda directory, cutoff_date, pattern="*": {"files_removed": 4, "space_freed": 128, "errors": []},
    )

    payload = tasks.cleanup_quarantine_task.run()

    assert payload == {
        "status": "success",
        "files_removed": 4,
        "space_freed": 128,
        "errors": [],
    }


def test_archive_processed_files_task_moves_old_files(tmp_path: Path, monkeypatch):
    safe_dir = tmp_path / "safe"
    safe_dir.mkdir()
    monkeypatch.setattr(tasks.settings, "safe_storage_dir", str(safe_dir))
    monkeypatch.setattr(tasks.settings, "archive_days_old", 30)

    old_file = safe_dir / "invoice.pdf"
    old_file.write_text("data", encoding="utf-8")
    old_ts = (datetime.now() - timedelta(days=40)).timestamp()
    import os
    os.utime(old_file, (old_ts, old_ts))

    payload = tasks.archive_processed_files_task.run()

    assert payload["status"] == "success"
    assert payload["files_archived"] == 1
    archive_dir = safe_dir.parent / "archive"
    archived_files = list(archive_dir.glob("**/invoice.pdf"))
    assert len(archived_files) == 1
    assert not old_file.exists()


def test_archive_processed_files_task_returns_failed_on_error(monkeypatch):
    monkeypatch.setattr(tasks.settings, "safe_storage_dir", "/dev/null/forbidden")

    payload = tasks.archive_processed_files_task.run()

    assert payload["status"] == "failed"
    assert "error" in payload
