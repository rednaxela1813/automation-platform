from pathlib import Path

from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository


def test_claim_new_invoice(tmp_path: Path):
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")

    assert repo.claim("key-1") is True


def test_claim_duplicate_invoice(tmp_path: Path):
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")

    assert repo.claim("key-1") is True
    assert repo.claim("key-1") is False


def test_mark_done(tmp_path: Path):
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")

    repo.claim("key-1")
    repo.mark_done("key-1")
