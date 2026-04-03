from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("httpx")

from automation.api.endpoints import service


def test_check_storage_ready_returns_ok(tmp_path, monkeypatch):
    safe_dir = tmp_path / "safe"
    quarantine_dir = tmp_path / "quarantine"
    monkeypatch.setattr(service.settings, "safe_storage_dir", str(safe_dir))
    monkeypatch.setattr(service.settings, "quarantine_dir", str(quarantine_dir))

    result = service._check_storage_ready()

    assert result.status == "ok"
    assert safe_dir.exists()
    assert quarantine_dir.exists()


def test_check_database_ready_for_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(service.settings, "database_url", f"sqlite:///{tmp_path / 'db.sqlite3'}")

    result = service._check_database_ready()

    assert result.status == "ok"


def test_check_database_ready_for_postgres_failure(monkeypatch):
    monkeypatch.setattr(service.settings, "database_url", "postgresql://user:pass@localhost/db")
    monkeypatch.setattr(
        service,
        "create_engine_from_settings",
        lambda url: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    result = service._check_database_ready()

    assert result.status == "fail"
    assert "db down" in result.details


def test_check_database_ready_unsupported_scheme(monkeypatch):
    monkeypatch.setattr(service.settings, "database_url", "mysql://localhost/db")

    result = service._check_database_ready()

    assert result.status == "fail"
    assert "Unsupported" in result.details


def test_check_redis_ready_ok(monkeypatch):
    class DummyRedis:
        def ping(self):
            return True

    monkeypatch.setattr(service.Redis, "from_url", lambda *args, **kwargs: DummyRedis())

    result = service._check_redis_ready()

    assert result.status == "ok"


def test_check_redis_ready_fail_on_exception(monkeypatch):
    monkeypatch.setattr(
        service.Redis,
        "from_url",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("redis down")),
    )

    result = service._check_redis_ready()

    assert result.status == "fail"
    assert "redis down" in result.details
