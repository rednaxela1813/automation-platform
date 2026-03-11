from __future__ import annotations

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from automation.api.endpoints import service
from automation.api.endpoints.service import ReadinessDependency
from automation.main import create_app


def _build_client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_api_info_endpoint():
    client = _build_client()
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["docs"] == "/docs"
    client.close()


def test_health_live_and_compat_endpoint():
    client = _build_client()

    live_response = client.get("/health/live")
    assert live_response.status_code == 200
    assert live_response.json()["status"] == "alive"

    compat_response = client.get("/health")
    assert compat_response.status_code == 200
    assert compat_response.json()["status"] == "alive"

    client.close()


def test_health_ready_returns_200_when_all_checks_pass(monkeypatch):
    monkeypatch.setattr(service, "_check_storage_ready", lambda: ReadinessDependency(status="ok"))
    monkeypatch.setattr(service, "_check_sqlite_ready", lambda: ReadinessDependency(status="ok"))
    monkeypatch.setattr(service, "_check_redis_ready", lambda: ReadinessDependency(status="ok"))

    client = _build_client()
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    client.close()


def test_health_ready_returns_503_when_any_check_fails(monkeypatch):
    monkeypatch.setattr(service, "_check_storage_ready", lambda: ReadinessDependency(status="ok"))
    monkeypatch.setattr(service, "_check_sqlite_ready", lambda: ReadinessDependency(status="ok"))
    monkeypatch.setattr(
        service,
        "_check_redis_ready",
        lambda: ReadinessDependency(status="fail", details="redis unavailable"),
    )

    client = _build_client()
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["checks"]["redis"]["status"] == "fail"
    client.close()
