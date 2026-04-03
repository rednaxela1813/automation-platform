from __future__ import annotations

import json
from pathlib import Path

import pytest

from automation.adapters.file_storage import LocalFileStorage
from automation.ports.email import EmailAttachment
from automation.ports.file_storage import FileStorageResult


@pytest.fixture
def storage_service(tmp_path: Path, monkeypatch) -> LocalFileStorage:
    monkeypatch.setattr("automation.adapters.file_storage.settings.safe_storage_dir", str(tmp_path / "safe"))
    monkeypatch.setattr(
        "automation.adapters.file_storage.settings.quarantine_dir", str(tmp_path / "quarantine")
    )
    monkeypatch.setattr("automation.adapters.file_storage.settings.max_file_size_mb", 1)
    monkeypatch.setattr(
        "automation.adapters.file_storage.settings.allowed_file_extensions",
        [".pdf", ".xlsx", ".docx", ".xml", ".csv"],
    )
    monkeypatch.setattr(
        "automation.adapters.file_storage.settings.allowed_mime_types",
        [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/xml",
            "text/xml",
        ],
    )
    return LocalFileStorage()


def test_store_attachment_saves_safe_file_and_metadata(
    storage_service: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(
        storage_service.security_scanner,
        "scan_file_content",
        lambda content, filename: (True, None),
    )
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4 sample",
        size=15,
    )

    result, file_path = storage_service.store_attachment(attachment)

    assert result == FileStorageResult.SAFE_STORAGE
    saved_path = Path(file_path)
    metadata_path = saved_path.with_suffix(".metadata.json")
    assert saved_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["original_filename"] == "invoice.pdf"
    assert metadata["content_type"] == "application/pdf"


def test_store_attachment_quarantines_blocked_extension(
    storage_service: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(
        storage_service.security_scanner,
        "scan_file_content",
        lambda content, filename: (True, None),
    )
    attachment = EmailAttachment(
        filename="payload.exe",
        content_type="application/octet-stream",
        content=b"MZ",
        size=2,
    )

    result, file_path = storage_service.store_attachment(attachment)

    assert result == FileStorageResult.QUARANTINE
    quarantined_path = Path(file_path)
    info_path = quarantined_path.with_suffix(".quarantine_info.json")
    assert quarantined_path.exists()
    assert info_path.exists()
    assert "Blocked extension" in info_path.read_text(encoding="utf-8")


def test_is_file_safe_allows_octet_stream_for_allowed_extension(
    storage_service: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(
        storage_service.security_scanner,
        "scan_file_content",
        lambda content, filename: (True, None),
    )
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/octet-stream",
        content=b"%PDF-1.4 sample",
        size=15,
    )

    assert storage_service.is_file_safe(attachment) is True


def test_is_file_safe_rejects_suspicious_content(
    storage_service: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(
        storage_service.security_scanner,
        "scan_file_content",
        lambda content, filename: (True, None),
    )
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"<script>alert('x')</script>",
        size=27,
    )

    assert storage_service.is_file_safe(attachment) is False


def test_is_file_safe_rejects_when_security_scanner_blocks(
    storage_service: LocalFileStorage, monkeypatch
):
    monkeypatch.setattr(
        storage_service.security_scanner,
        "scan_file_content",
        lambda content, filename: (False, "virus"),
    )
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.4 sample",
        size=15,
    )

    assert storage_service.is_file_safe(attachment) is False


def test_delete_quarantine_file_removes_existing_file(storage_service: LocalFileStorage):
    file_path = storage_service.quarantine_dir / "payload.exe"
    file_path.write_bytes(b"malicious")

    assert storage_service.delete_quarantine_file("payload.exe") is True
    assert not file_path.exists()
