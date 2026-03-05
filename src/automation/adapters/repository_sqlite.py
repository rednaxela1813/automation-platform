from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from automation.ports.repository import ProcessedInvoiceRepository
from automation.config.settings import settings


class SqliteProcessedInvoiceRepository(ProcessedInvoiceRepository):
    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path)
        self._init_table()

    def _init_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_invoices (
                invoice_key TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT NOT NULL,
                next_retry_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def claim(self, invoice_key: str) -> bool:
        try:
            now = datetime.now(UTC).isoformat()
            self._conn.execute(
                """
                INSERT INTO processed_invoices (invoice_key, status, updated_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (invoice_key, "received", now, now),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def mark_done(self, invoice_key: str) -> None:
        self._conn.execute(
            """
            UPDATE processed_invoices
            SET status = ?, updated_at = ?
            WHERE invoice_key = ?
            """,
            ("done", datetime.now(UTC).isoformat(), invoice_key),
        )
        self._conn.commit()

    def mark_failed(self, invoice_key: str, error: str) -> None:
        cursor = self._conn.execute(
            "SELECT attempts FROM processed_invoices WHERE invoice_key = ?",
            (invoice_key,),
        )
        row = cursor.fetchone()
        
        if row is None:
            return  # Invoice key doesn't exist
            
        attempts = row[0] + 1
        now = datetime.now(UTC)
        
        # Calculate next retry time with exponential backoff
        next_retry_at = None
        if attempts <= settings.max_retry_attempts:
            backoff_minutes = settings.retry_backoff_minutes * (2 ** (attempts - 1))
            next_retry_at = now + timedelta(minutes=backoff_minutes)
        
        # Determine final status
        if attempts > settings.max_retry_attempts:
            status = "failed_permanently"
        else:
            status = "failed_retryable"
            
        self._conn.execute(
            """
            UPDATE processed_invoices
            SET status = ?, last_error = ?, attempts = ?, updated_at = ?, next_retry_at = ?
            WHERE invoice_key = ?
            """,
            (
                status, 
                error, 
                attempts, 
                now.isoformat(), 
                next_retry_at.isoformat() if next_retry_at else None,
                invoice_key
            ),
        )
        self._conn.commit()

    def get_retryable_items(self) -> List[str]:
        """Get invoice keys that are eligible for retry."""
        now = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            """
            SELECT invoice_key FROM processed_invoices 
            WHERE status = 'failed_retryable' 
            AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY updated_at ASC
            """,
            (now,),
        )
        return [row[0] for row in cursor.fetchall()]

    def reset_for_retry(self, invoice_key: str) -> bool:
        """Reset an item for retry by changing status back to received."""
        rows_affected = self._conn.execute(
            """
            UPDATE processed_invoices 
            SET status = 'received', updated_at = ?, next_retry_at = NULL
            WHERE invoice_key = ? AND status = 'failed_retryable'
            """,
            (datetime.now(UTC).isoformat(), invoice_key),
        ).rowcount
        self._conn.commit()
        return rows_affected > 0

    def get_status_summary(self) -> dict[str, int]:
        """Get count of items by status for monitoring."""
        cursor = self._conn.execute(
            """
            SELECT status, COUNT(*) 
            FROM processed_invoices 
            GROUP BY status
            """
        )
        return {status: count for status, count in cursor.fetchall()}

    def cleanup_old_records(self, days_old: int = 90) -> int:
        """Remove old completed records to prevent table bloat."""
        cutoff_date = (datetime.now(UTC) - timedelta(days=days_old)).isoformat()
        rows_affected = self._conn.execute(
            """
            DELETE FROM processed_invoices 
            WHERE status = 'done' AND updated_at < ?
            """,
            (cutoff_date,),
        ).rowcount
        self._conn.commit()
        return rows_affected
