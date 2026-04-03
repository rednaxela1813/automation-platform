from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

import automation.api.dependencies as deps


def test_dependency_factories_return_instances(monkeypatch):
    monkeypatch.setattr(deps, "ImapEmailClient", lambda: "imap")
    monkeypatch.setattr(deps, "LocalFileStorage", lambda: "storage")
    monkeypatch.setattr(deps, "get_document_parsers", lambda: ["parser"])

    assert asyncio.run(deps.get_email_processor()) == "imap"
    assert asyncio.run(deps.get_file_storage()) == "storage"
    assert asyncio.run(deps.get_document_parser()) == ["parser"]


def test_verify_api_key_allows_when_not_configured(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: type("S", (), {"api_key": ""})())

    assert asyncio.run(deps.verify_api_key("anything")) is True


def test_verify_api_key_rejects_invalid_key(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: type("S", (), {"api_key": "secret"})())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(deps.verify_api_key("wrong"))

    assert exc.value.status_code == 401


def test_verify_api_key_accepts_valid_key(monkeypatch):
    monkeypatch.setattr(deps, "get_settings", lambda: type("S", (), {"api_key": "secret"})())

    assert asyncio.run(deps.verify_api_key("secret")) is True
