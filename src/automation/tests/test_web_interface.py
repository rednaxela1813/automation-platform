from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from automation.main import create_app


def _build_client(tmp_path: Path) -> TestClient:
    safe_dir = tmp_path / "storage" / "safe"
    quarantine_dir = tmp_path / "storage" / "quarantine"
    log_dir = tmp_path / "logs"
    safe_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    import automation.web.interface as web

    web.settings.safe_storage_dir = str(safe_dir)
    web.settings.quarantine_dir = str(quarantine_dir)
    web.settings.log_dir = str(log_dir)
    web.settings.allowed_file_extensions = [".pdf", ".csv", ".xml", ".xlsx"]
    web.settings.default_page_limit = 50
    web.settings.imap_host = "imap.example.com"
    web.settings.imap_port = 993
    web.settings.imap_user = "user@example.com"
    web.settings.imap_password = "secret"
    web.settings.imap_mailbox = "INBOX"
    web.settings.max_file_size_mb = 50
    web.settings.scan_interval_minutes = 5

    app = create_app()
    return TestClient(app)


def test_dashboard_renders_stats_and_recent_files(tmp_path: Path):
    client = _build_client(tmp_path)
    safe_file = tmp_path / "storage" / "safe" / "invoice.pdf"
    safe_file.write_text("pdf", encoding="utf-8")
    quarantine_file = tmp_path / "storage" / "quarantine" / "bad.exe"
    quarantine_file.write_text("exe", encoding="utf-8")
    quarantine_file.with_suffix(".quarantine_info.json").write_text(
        json.dumps({"quarantine_reason": "Blocked extension"}),
        encoding="utf-8",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert "invoice.pdf" in response.text
    assert "bad.exe" in response.text
    client.close()


def test_settings_page_renders_configuration(tmp_path: Path):
    client = _build_client(tmp_path)

    response = client.get("/settings")

    assert response.status_code == 200
    assert "Settings" in response.text
    assert "imap.example.com" in response.text
    client.close()


def test_files_page_lists_files_and_pdf_count(tmp_path: Path):
    client = _build_client(tmp_path)
    (tmp_path / "storage" / "safe" / "invoice.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "storage" / "safe" / "report.csv").write_text("csv", encoding="utf-8")

    response = client.get("/files")

    assert response.status_code == 200
    assert "invoice.pdf" in response.text
    assert "report.csv" in response.text
    client.close()


def test_logs_page_reads_tail_from_log_file(tmp_path: Path):
    client = _build_client(tmp_path)
    log_file = tmp_path / "logs" / "automation.log"
    log_file.write_text("line1\nline2\n", encoding="utf-8")

    response = client.get("/logs")

    assert response.status_code == 200
    assert "line1" in response.text
    assert "line2" in response.text
    client.close()


def test_web_stats_endpoint_returns_json(tmp_path: Path):
    client = _build_client(tmp_path)
    (tmp_path / "storage" / "safe" / "invoice.pdf").write_text("pdf", encoding="utf-8")

    response = client.get("/api/web/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["files_in_safe_storage"] == 1
    assert data["system_status"] == "Active"
    client.close()


def test_connection_status_endpoint_reflects_config(tmp_path: Path):
    client = _build_client(tmp_path)

    response = client.get("/api/web/connection-status")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert "last_check" in data
    client.close()


def test_test_connection_web_returns_success(monkeypatch, tmp_path: Path):
    client = _build_client(tmp_path)

    class DummyImap:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username, password):
            assert username == "user@example.com"
            assert password == "secret"
            return "OK", [b"logged"]

        def select(self, mailbox):
            assert mailbox == "INBOX"
            return "OK", [b"1"]

    monkeypatch.setattr("automation.web.interface.imaplib.IMAP4_SSL", lambda host, port: DummyImap())

    response = client.post(
        "/api/web/test-connection",
        data={
            "imap_host": "imap.example.com",
            "imap_port": "993",
            "imap_username": "user@example.com",
            "imap_password": "secret",
            "imap_mailbox": "INBOX",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    client.close()


def test_test_connection_web_returns_auth_error(monkeypatch, tmp_path: Path):
    client = _build_client(tmp_path)

    class DummyImap:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username, password):
            raise __import__("imaplib").IMAP4.error("bad auth")

    monkeypatch.setattr("automation.web.interface.imaplib.IMAP4_SSL", lambda host, port: DummyImap())

    response = client.post(
        "/api/web/test-connection",
        data={
            "imap_host": "imap.example.com",
            "imap_port": "993",
            "imap_username": "user@example.com",
            "imap_password": "secret",
            "imap_mailbox": "INBOX",
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert "IMAP auth failed" in response.json()["error"]
    client.close()


def test_test_connection_web_rejects_missing_required_form_fields(tmp_path: Path):
    client = _build_client(tmp_path)

    response = client.post(
        "/api/web/test-connection",
        data={
            "imap_host": "",
            "imap_port": "993",
            "imap_username": "",
            "imap_password": "",
            "imap_mailbox": "INBOX",
        },
    )

    assert response.status_code == 422
    client.close()
