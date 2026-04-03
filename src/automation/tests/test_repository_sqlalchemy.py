from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from automation.adapters.repository_sqlalchemy import SqlAlchemyProcessedInvoiceRepository
from automation.db.base import Base
from automation.db.models import ProcessedInvoiceRecord


@pytest.fixture
def repository(tmp_path) -> SqlAlchemyProcessedInvoiceRepository:
    repo = SqlAlchemyProcessedInvoiceRepository(f"sqlite:///{tmp_path / 'repo.db'}")
    Base.metadata.create_all(repo._engine)
    return repo


def _get_record(repository: SqlAlchemyProcessedInvoiceRepository, invoice_key: str) -> ProcessedInvoiceRecord | None:
    with Session(repository._engine) as session:
        return session.get(ProcessedInvoiceRecord, invoice_key)


def test_claim_is_idempotent(repository: SqlAlchemyProcessedInvoiceRepository):
    assert repository.claim("inv-1") is True
    assert repository.claim("inv-1") is False

    record = _get_record(repository, "inv-1")
    assert record is not None
    assert record.status == "received"
    assert record.attempts == 0


def test_mark_done_updates_existing_record(repository: SqlAlchemyProcessedInvoiceRepository):
    repository.claim("inv-1")

    repository.mark_done("inv-1")

    record = _get_record(repository, "inv-1")
    assert record is not None
    assert record.status == "done"


def test_mark_failed_sets_retryable_status_and_backoff(monkeypatch, repository: SqlAlchemyProcessedInvoiceRepository):
    monkeypatch.setattr("automation.adapters.repository_sqlalchemy.settings.max_retry_attempts", 3)
    monkeypatch.setattr("automation.adapters.repository_sqlalchemy.settings.retry_backoff_minutes", 15)
    repository.claim("inv-1")

    before = datetime.now(UTC)
    repository.mark_failed("inv-1", "boom")
    after = datetime.now(UTC)

    record = _get_record(repository, "inv-1")
    assert record is not None
    assert record.status == "failed_retryable"
    assert record.attempts == 1
    assert record.last_error == "boom"
    assert record.next_retry_at is not None
    expected = before.replace(tzinfo=None) + timedelta(minutes=15)
    actual = record.next_retry_at.replace(tzinfo=None)
    assert abs((actual - expected).total_seconds()) < 5


def test_mark_failed_sets_permanent_status_after_max_retries(monkeypatch, repository: SqlAlchemyProcessedInvoiceRepository):
    monkeypatch.setattr("automation.adapters.repository_sqlalchemy.settings.max_retry_attempts", 1)
    monkeypatch.setattr("automation.adapters.repository_sqlalchemy.settings.retry_backoff_minutes", 15)
    repository.claim("inv-1")

    repository.mark_failed("inv-1", "first")
    repository.mark_failed("inv-1", "second")

    record = _get_record(repository, "inv-1")
    assert record is not None
    assert record.status == "failed_permanently"
    assert record.attempts == 2
    assert record.next_retry_at is None


def test_get_retryable_items_returns_only_due_retryable_records(repository: SqlAlchemyProcessedInvoiceRepository):
    now = datetime.now(UTC)
    with Session(repository._engine) as session:
        session.add_all(
            [
                ProcessedInvoiceRecord(
                    invoice_key="due",
                    status="failed_retryable",
                    attempts=1,
                    last_error="x",
                    updated_at=now - timedelta(minutes=2),
                    next_retry_at=now - timedelta(minutes=1),
                    created_at=now - timedelta(days=1),
                ),
                ProcessedInvoiceRecord(
                    invoice_key="future",
                    status="failed_retryable",
                    attempts=1,
                    last_error="x",
                    updated_at=now - timedelta(minutes=1),
                    next_retry_at=now + timedelta(hours=1),
                    created_at=now - timedelta(days=1),
                ),
                ProcessedInvoiceRecord(
                    invoice_key="done",
                    status="done",
                    attempts=0,
                    last_error=None,
                    updated_at=now - timedelta(minutes=3),
                    next_retry_at=None,
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        session.commit()

    assert repository.get_retryable_items() == ["due"]


def test_reset_for_retry_only_updates_failed_retryable(repository: SqlAlchemyProcessedInvoiceRepository):
    now = datetime.now(UTC)
    with Session(repository._engine) as session:
        session.add(
            ProcessedInvoiceRecord(
                invoice_key="inv-1",
                status="failed_retryable",
                attempts=2,
                last_error="boom",
                updated_at=now - timedelta(minutes=1),
                next_retry_at=now,
                created_at=now - timedelta(days=1),
            )
        )
        session.commit()

    assert repository.reset_for_retry("inv-1") is True

    record = _get_record(repository, "inv-1")
    assert record is not None
    assert record.status == "received"
    assert record.next_retry_at is None


def test_get_status_summary_counts_statuses(repository: SqlAlchemyProcessedInvoiceRepository):
    now = datetime.now(UTC)
    with Session(repository._engine) as session:
        session.add_all(
            [
                ProcessedInvoiceRecord(
                    invoice_key="a",
                    status="done",
                    attempts=0,
                    last_error=None,
                    updated_at=now,
                    next_retry_at=None,
                    created_at=now,
                ),
                ProcessedInvoiceRecord(
                    invoice_key="b",
                    status="done",
                    attempts=0,
                    last_error=None,
                    updated_at=now,
                    next_retry_at=None,
                    created_at=now,
                ),
                ProcessedInvoiceRecord(
                    invoice_key="c",
                    status="failed_retryable",
                    attempts=1,
                    last_error="x",
                    updated_at=now,
                    next_retry_at=now,
                    created_at=now,
                ),
            ]
        )
        session.commit()

    assert repository.get_status_summary() == {"done": 2, "failed_retryable": 1}


def test_cleanup_old_records_deletes_only_old_done_records(repository: SqlAlchemyProcessedInvoiceRepository):
    now = datetime.now(UTC)
    with Session(repository._engine) as session:
        session.add_all(
            [
                ProcessedInvoiceRecord(
                    invoice_key="old-done",
                    status="done",
                    attempts=0,
                    last_error=None,
                    updated_at=now - timedelta(days=120),
                    next_retry_at=None,
                    created_at=now - timedelta(days=120),
                ),
                ProcessedInvoiceRecord(
                    invoice_key="recent-done",
                    status="done",
                    attempts=0,
                    last_error=None,
                    updated_at=now - timedelta(days=10),
                    next_retry_at=None,
                    created_at=now - timedelta(days=10),
                ),
                ProcessedInvoiceRecord(
                    invoice_key="old-failed",
                    status="failed_retryable",
                    attempts=1,
                    last_error="x",
                    updated_at=now - timedelta(days=120),
                    next_retry_at=now - timedelta(days=1),
                    created_at=now - timedelta(days=120),
                ),
            ]
        )
        session.commit()

    deleted = repository.cleanup_old_records(days_old=90)

    assert deleted == 1
    assert _get_record(repository, "old-done") is None
    assert _get_record(repository, "recent-done") is not None
    assert _get_record(repository, "old-failed") is not None
