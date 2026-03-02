from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from automation.api.dependencies import get_settings
from automation.config.settings import Settings
from automation.main import create_app


def _build_test_settings(tmp_path: Path) -> Settings:
    storage_root = tmp_path / "storage"
    safe_dir = storage_root / "safe"
    quarantine_dir = storage_root / "quarantine"
    safe_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        imap_host="imap.example.com",
        imap_user="user@example.com",
        imap_password="secret",
        safe_storage_dir=str(safe_dir),
        quarantine_dir=str(quarantine_dir),
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        redis_url="redis://localhost:6379/0",
    )


def _build_client(tmp_path: Path) -> TestClient:
    app = create_app()
    settings = _build_test_settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_get_processing_status_returns_idle(tmp_path: Path):
    client = _build_client(tmp_path)

    response = client.get("/api/v1/emails/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "idle"
    assert data["emails_processed"] == 0
    assert data["files_processed"] == 0
    assert data["files_quarantined"] == 0

    client.close()


def test_trigger_email_processing_starts_background_task(tmp_path: Path, monkeypatch):
    client = _build_client(tmp_path)

    async def noop_task(force_reprocess: bool = False, dry_run: bool = False):
        _ = (force_reprocess, dry_run)

    monkeypatch.setattr("automation.api.endpoints.emails.process_emails_task", noop_task)

    response = client.post(
        "/api/v1/emails/process",
        json={"force_reprocess": True, "dry_run": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "background" in data["message"].lower()
    assert data["emails_processed"] == 0

    client.close()
