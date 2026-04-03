from __future__ import annotations

import json
import os
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
        cleanup_days_old=30,
    )


def _build_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    app = create_app()
    settings = _build_test_settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    return client, settings


def test_list_safe_files_returns_paginated_entries(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    (safe_dir / "a.pdf").write_text("a", encoding="utf-8")
    (safe_dir / "b.csv").write_text("b", encoding="utf-8")

    response = client.get("/api/v1/files/safe", params={"limit": 1, "offset": 0})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["files"]) == 1
    client.close()


def test_view_and_download_safe_file_return_ok(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    file_path = safe_dir / "invoice.pdf"
    file_path.write_bytes(b"%PDF")

    view = client.get("/api/v1/files/view/safe/invoice.pdf")
    download = client.get("/api/v1/files/download", params={"path": "safe/invoice.pdf"})

    assert view.status_code == 200
    assert download.status_code == 200
    assert "application/pdf" in view.headers["content-type"]
    client.close()


def test_file_info_returns_metadata(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    file_path = safe_dir / "invoice.pdf"
    file_path.write_bytes(b"%PDF")

    response = client.get("/api/v1/files/info", params={"path": "safe/invoice.pdf"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["filename"] == "invoice.pdf"
    assert data["mime_type"] == "application/pdf"
    client.close()


def test_get_parsed_file_data_returns_500_on_invalid_json(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    source_file = safe_dir / "invoice.pdf"
    source_file.write_bytes(b"%PDF")
    source_file.with_suffix(".parsed.json").write_text("{not-json", encoding="utf-8")

    response = client.get("/api/v1/files/parsed", params={"path": "safe/invoice.pdf"})

    assert response.status_code == 500
    assert "Failed to read parsed JSON" in response.json()["detail"]
    client.close()


def test_analyze_file_returns_not_implemented(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    (safe_dir / "invoice.pdf").write_bytes(b"%PDF")

    response = client.get("/api/v1/files/analyze", params={"path": "safe/invoice.pdf"})

    assert response.status_code == 501
    assert "not implemented" in response.text.lower()
    client.close()


def test_cleanup_old_files_removes_old_entries(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    old_file = safe_dir / "old.pdf"
    old_file.write_text("old", encoding="utf-8")
    old_ts = 946684800
    os.utime(old_file, (old_ts, old_ts))

    response = client.post("/api/v1/files/cleanup")

    assert response.status_code == 200
    assert response.json()["files_removed"] == 1
    assert not old_file.exists()
    client.close()


def test_list_quarantine_files_returns_unknown_reason_without_sidecar(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    quarantine_dir = Path(settings.quarantine_dir)
    (quarantine_dir / "blocked.exe").write_bytes(b"exe")

    response = client.get("/api/v1/files/quarantine")

    assert response.status_code == 200
    assert response.json()["files"][0]["quarantine_reason"] == "Unknown"
    client.close()


def test_delete_quarantine_file_removes_sidecar(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    quarantine_dir = Path(settings.quarantine_dir)
    quarantined = quarantine_dir / "blocked.exe"
    quarantined.write_bytes(b"exe")
    sidecar = quarantine_dir / "blocked.quarantine_info.json"
    sidecar.write_text(json.dumps({"quarantine_reason": "bad"}), encoding="utf-8")

    response = client.delete("/api/v1/files/quarantine/blocked.exe")

    assert response.status_code == 200
    assert not quarantined.exists()
    assert not sidecar.exists()
    client.close()
