from __future__ import annotations

import json
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


def _build_client(tmp_path: Path) -> tuple[TestClient, Settings]:
    app = create_app()
    settings = _build_test_settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    return client, settings


def test_get_parsed_file_data_success(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)

    source_file = safe_dir / "invoice.pdf"
    source_file.write_bytes(b"%PDF-1.4 test")
    parsed_file = source_file.with_suffix(".parsed.json")
    parsed_file.write_text(
        json.dumps({"success": True, "invoice": {"amount": "10.00", "currency": "EUR"}}),
        encoding="utf-8",
    )

    response = client.get("/api/v1/files/parsed", params={"path": "safe/invoice.pdf"})
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["source_file"] == "invoice.pdf"
    assert data["parsed_file"] == "invoice.parsed.json"
    assert data["data"]["invoice"]["amount"] == "10.00"

    client.close()


def test_get_parsed_file_data_not_found_when_missing_parsed_json(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)

    source_file = safe_dir / "invoice.pdf"
    source_file.write_bytes(b"%PDF-1.4 test")

    response = client.get("/api/v1/files/parsed", params={"path": "safe/invoice.pdf"})
    assert response.status_code == 404
    assert "Parsed JSON is not available" in response.json()["detail"]

    client.close()


def test_view_safe_file_blocks_path_traversal(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    _ = settings

    response = client.get("/api/v1/files/view/../../etc/passwd")
    assert response.status_code == 404

    client.close()


def test_delete_quarantine_file_success(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    quarantine_dir = Path(settings.quarantine_dir)

    quarantined = quarantine_dir / "quarantine_sample.pdf"
    quarantined.write_bytes(b"blocked")

    response = client.delete("/api/v1/files/quarantine/quarantine_sample.pdf")
    assert response.status_code == 200
    assert "deleted from quarantine" in response.json()["message"]
    assert not quarantined.exists()

    client.close()


def test_delete_quarantine_file_blocks_path_traversal(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)

    outside_file = safe_dir / "must_not_be_deleted.pdf"
    outside_file.write_bytes(b"keep")

    response = client.delete("/api/v1/files/quarantine/../safe/must_not_be_deleted.pdf")
    assert response.status_code in (400, 404)
    assert outside_file.exists()

    client.close()


def test_list_quarantine_files_excludes_sidecar_info_files(tmp_path: Path):
    client, settings = _build_client(tmp_path)
    quarantine_dir = Path(settings.quarantine_dir)

    quarantined = quarantine_dir / "quarantine_sample.csv"
    quarantined.write_bytes(b"id,amount\n1,10")
    sidecar = quarantine_dir / "quarantine_sample.quarantine_info.json"
    sidecar.write_text(
        json.dumps({"quarantine_reason": "Unsupported extension"}),
        encoding="utf-8",
    )

    response = client.get("/api/v1/files/quarantine")
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert len(data["files"]) == 1
    assert data["files"][0]["name"] == "quarantine_sample.csv"
    assert data["files"][0]["quarantine_reason"] == "Unsupported extension"

    client.close()
