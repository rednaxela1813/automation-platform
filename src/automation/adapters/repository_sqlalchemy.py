from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from automation.config.settings import settings
from automation.db.models import ProcessedInvoiceRecord
from automation.db.session import create_engine_from_settings
from automation.ports.repository import ProcessedInvoiceRepository


class SqlAlchemyProcessedInvoiceRepository(ProcessedInvoiceRepository):
    def __init__(self, database_url: str):
        self._engine = create_engine_from_settings(database_url)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, expire_on_commit=False)

    def claim(self, invoice_key: str) -> bool:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            session.add(
                ProcessedInvoiceRecord(
                    invoice_key=invoice_key,
                    status="received",
                    attempts=0,
                    updated_at=now,
                    created_at=now,
                )
            )
            try:
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False

    def mark_done(self, invoice_key: str) -> None:
        with self._session_factory() as session:
            record = session.get(ProcessedInvoiceRecord, invoice_key)
            if record is None:
                return
            record.status = "done"
            record.updated_at = datetime.now(UTC)
            session.commit()

    def mark_failed(self, invoice_key: str, error: str) -> None:
        with self._session_factory() as session:
            record = session.get(ProcessedInvoiceRecord, invoice_key)
            if record is None:
                return

            attempts = record.attempts + 1
            now = datetime.now(UTC)
            next_retry_at = None
            if attempts <= settings.max_retry_attempts:
                backoff_minutes = settings.retry_backoff_minutes * (2 ** (attempts - 1))
                next_retry_at = now + timedelta(minutes=backoff_minutes)

            record.attempts = attempts
            record.last_error = error
            record.updated_at = now
            record.next_retry_at = next_retry_at
            record.status = (
                "failed_permanently" if attempts > settings.max_retry_attempts else "failed_retryable"
            )
            session.commit()

    def get_retryable_items(self) -> list[str]:
        now = datetime.now(UTC)
        with self._session_factory() as session:
            rows = session.execute(
                select(ProcessedInvoiceRecord.invoice_key)
                .where(ProcessedInvoiceRecord.status == "failed_retryable")
                .where(
                    (ProcessedInvoiceRecord.next_retry_at.is_(None))
                    | (ProcessedInvoiceRecord.next_retry_at <= now)
                )
                .order_by(ProcessedInvoiceRecord.updated_at.asc())
            ).all()
            return [row[0] for row in rows]

    def reset_for_retry(self, invoice_key: str) -> bool:
        with self._session_factory() as session:
            record = session.get(ProcessedInvoiceRecord, invoice_key)
            if record is None or record.status != "failed_retryable":
                return False
            record.status = "received"
            record.updated_at = datetime.now(UTC)
            record.next_retry_at = None
            session.commit()
            return True

    def get_status_summary(self) -> dict[str, int]:
        with self._session_factory() as session:
            rows = session.execute(select(ProcessedInvoiceRecord.status)).scalars().all()
            summary: dict[str, int] = {}
            for status in rows:
                summary[status] = summary.get(status, 0) + 1
            return summary

    def cleanup_old_records(self, days_old: int = 90) -> int:
        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
        with self._session_factory() as session:
            records = session.scalars(
                select(ProcessedInvoiceRecord).where(
                    ProcessedInvoiceRecord.status == "done",
                    ProcessedInvoiceRecord.updated_at < cutoff_date,
                )
            ).all()
            deleted_count = len(records)
            for record in records:
                session.delete(record)
            session.commit()
            return deleted_count
