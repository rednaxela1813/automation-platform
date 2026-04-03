from __future__ import annotations

import socket
import zipfile
from io import BytesIO

import pytest

from automation.adapters.security_scanner import SecurityScanner


def test_scan_file_content_blocks_dangerous_extension():
    scanner = SecurityScanner()

    is_safe, reason = scanner.scan_file_content(b"echo hi", "payload.exe")

    assert is_safe is False
    assert "Dangerous file extension" in reason


def test_is_zip_bomb_detects_excessive_ratio(monkeypatch):
    monkeypatch.setattr("automation.adapters.security_scanner.settings.max_archive_ratio", 2.0)
    scanner = SecurityScanner()

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("huge.txt", "A" * 10000)

    assert scanner._is_zip_bomb(buffer.getvalue(), "archive.zip") is True


def test_is_zip_bomb_ignores_non_zip_extensions():
    scanner = SecurityScanner()

    assert scanner._is_zip_bomb(b"not-an-archive", "archive.pdf") is False


def test_validate_pdf_limits_returns_false_on_parser_error(monkeypatch):
    scanner = SecurityScanner()

    def raise_error(_):
        raise ValueError("bad pdf")

    monkeypatch.setattr("automation.adapters.security_scanner.pdfplumber.open", raise_error)

    assert scanner._validate_pdf_limits(b"%PDF-1.4") is False


def test_validate_pdf_limits_blocks_too_many_pages(monkeypatch):
    monkeypatch.setattr("automation.adapters.security_scanner.settings.max_pdf_pages", 1)
    scanner = SecurityScanner()

    class DummyPdf:
        def __init__(self):
            self.pages = [DummyPage("one"), DummyPage("two")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

    monkeypatch.setattr("automation.adapters.security_scanner.pdfplumber.open", lambda _: DummyPdf())

    assert scanner._validate_pdf_limits(b"%PDF-1.4") is False


def test_scan_with_clamav_returns_virus_name(monkeypatch):
    scanner = SecurityScanner()

    class DummySocket:
        def connect(self, path):
            self.path = path

        def sendall(self, data):
            self.last = data

        def recv(self, size):
            return b"stream: Eicar-Test-Signature FOUND"

        def close(self):
            return None

    monkeypatch.setattr("automation.adapters.security_scanner.socket.socket", lambda *args: DummySocket())

    assert scanner._scan_with_clamav(b"content") == "Eicar-Test-Signature"


def test_scan_with_clamav_returns_scan_failure_on_socket_error(monkeypatch):
    scanner = SecurityScanner()

    class DummySocket:
        def connect(self, path):
            raise socket.error("connect failed")

    monkeypatch.setattr("automation.adapters.security_scanner.socket.socket", lambda *args: DummySocket())

    assert scanner._scan_with_clamav(b"content") == "SCAN_FAILURE"
