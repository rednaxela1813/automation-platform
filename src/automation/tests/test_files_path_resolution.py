from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import HTTPException

os.environ["DEBUG"] = "false"

from automation.api.endpoints.files import _resolve_quarantine_file
from automation.config.settings import Settings


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


def test_resolve_quarantine_file_blocks_path_traversal(tmp_path: Path):
    settings = _build_test_settings(tmp_path)
    safe_dir = Path(settings.safe_storage_dir)

    outside_file = safe_dir / "must_not_be_deleted.pdf"
    outside_file.write_bytes(b"keep")

    with pytest.raises(HTTPException) as exc:
        _resolve_quarantine_file("../safe/must_not_be_deleted.pdf", settings)
    assert exc.value.status_code == 404
    assert outside_file.exists()
