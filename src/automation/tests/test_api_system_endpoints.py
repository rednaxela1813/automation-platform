from __future__ import annotations

import imaplib
from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from automation.api.dependencies import get_settings
from automation.config.settings import Settings
from automation.main import create_app


def _build_test_settings(tmp_path: Path, *, with_credentials: bool = True) -> Settings:
    storage_root = tmp_path / "storage"
    safe_dir = storage_root / "safe"
    quarantine_dir = storage_root / "quarantine"
    safe_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        imap_host="imap.example.com",
        imap_user="user@example.com" if with_credentials else "",
        imap_password="secret" if with_credentials else "",
        imap_port=993,
        imap_mailbox="INBOX",
        max_file_size_mb=25,
        allowed_file_extensions=[".pdf", ".xlsx"],
        scan_interval_minutes=10,
        safe_storage_dir=str(safe_dir),
        quarantine_dir=str(quarantine_dir),
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        redis_url="redis://localhost:6379/0",
    )


def _build_client(tmp_path: Path, *, with_credentials: bool = True) -> tuple[TestClient, Settings]:
    app = create_app()
    settings = _build_test_settings(tmp_path, with_credentials=with_credentials)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    return client, settings


def test_get_system_stats_returns_file_counts(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)
    quarantine_dir = Path(settings.quarantine_dir)

    (safe_dir / "a.pdf").write_bytes(b"a")
    (safe_dir / "b.pdf").write_bytes(b"b")
    (quarantine_dir / "c.pdf").write_bytes(b"c")

    response = client.get("/api/v1/system/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["files_in_safe_storage"] == 2
    assert data["files_in_quarantine"] == 1
    assert data["system_status"] == "healthy"

    client.close()


def test_get_system_config_uses_effective_settings(tmp_path: Path):
    client, settings = _build_client(tmp_path)

    response = client.get("/api/v1/system/config")
    assert response.status_code == 200
    data = response.json()

    assert data["imap_host"] == settings.imap_host
    assert data["imap_mailbox"] == settings.imap_mailbox
    assert data["max_file_size_mb"] == settings.max_file_size_mb
    assert data["allowed_extensions"] == settings.allowed_file_extensions
    assert data["scan_interval_minutes"] == settings.scan_interval_minutes

    client.close()


def test_test_imap_connection_returns_error_without_credentials(tmp_path: Path):
    client, _ = _build_client(tmp_path, with_credentials=False)

    response = client.post("/api/v1/system/test-connection")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "failed"
    assert "credentials" in data["error"].lower()

    client.close()


def test_test_imap_connection_success(tmp_path: Path, monkeypatch):
    client, settings = _build_client(tmp_path, with_credentials=True)

    class DummyImap:
        def __init__(self, host: str, port: int):
            assert host == settings.imap_host
            assert port == settings.imap_port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username: str, password: str):
            assert username == settings.imap_user
            assert password == settings.imap_password

        def select(self, mailbox: str):
            assert mailbox == settings.imap_mailbox
            return "OK", [b"1"]

    monkeypatch.setattr("automation.api.endpoints.system.imaplib.IMAP4_SSL", DummyImap)

    response = client.post("/api/v1/system/test-connection")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "success"
    assert data["server"] == settings.imap_host

    client.close()


def test_test_imap_connection_auth_error(tmp_path: Path, monkeypatch):
    client, _ = _build_client(tmp_path, with_credentials=True)

    class FailingImap:
        def __init__(self, host: str, port: int):
            _ = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username: str, password: str):
            _ = (username, password)
            raise imaplib.IMAP4.error("bad credentials")

    monkeypatch.setattr("automation.api.endpoints.system.imaplib.IMAP4_SSL", FailingImap)

    response = client.post("/api/v1/system/test-connection")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "failed"
    assert "auth failed" in data["error"].lower()

    client.close()
