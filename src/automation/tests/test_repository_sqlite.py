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

    summary = repo.get_status_summary()
    assert summary["done"] == 1


def test_mark_failed_sets_retryable_status(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.max_retry_attempts", 3)
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.retry_backoff_minutes", 15)
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")
    repo.claim("key-1")

    repo.mark_failed("key-1", "boom")

    summary = repo.get_status_summary()
    assert summary["failed_retryable"] == 1
    assert repo.get_retryable_items() == []


def test_mark_failed_sets_permanent_status_after_max_retries(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.max_retry_attempts", 1)
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.retry_backoff_minutes", 15)
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")
    repo.claim("key-1")

    repo.mark_failed("key-1", "first")
    repo.mark_failed("key-1", "second")

    summary = repo.get_status_summary()
    assert summary["failed_permanently"] == 1


def test_get_retryable_items_and_reset_for_retry(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.max_retry_attempts", 3)
    monkeypatch.setattr("automation.adapters.repository_sqlite.settings.retry_backoff_minutes", 0)
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")
    repo.claim("key-1")
    repo.mark_failed("key-1", "boom")

    assert repo.get_retryable_items() == ["key-1"]
    assert repo.reset_for_retry("key-1") is True
    assert repo.get_status_summary()["received"] == 1


def test_cleanup_old_records_deletes_only_old_done_records(tmp_path: Path):
    repo = SqliteProcessedInvoiceRepository(tmp_path / "test.db")
    repo.claim("old-done")
    repo.claim("recent-done")
    repo.claim("failed")
    repo.mark_done("old-done")
    repo.mark_done("recent-done")
    repo.mark_failed("failed", "boom")

    repo._conn.execute(
        "UPDATE processed_invoices SET updated_at = ? WHERE invoice_key = ?",
        ("2000-01-01T00:00:00+00:00", "old-done"),
    )
    repo._conn.commit()

    deleted = repo.cleanup_old_records(days_old=90)

    assert deleted == 1
    summary = repo.get_status_summary()
    assert "old-done" not in repo.get_retryable_items()
    assert summary["done"] == 1
    assert summary["failed_retryable"] == 1
