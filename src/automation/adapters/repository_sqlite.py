from __future__ import annotations

import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from automation.ports.repository import ProcessedInvoiceRepository


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
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def claim(self, invoice_key: str) -> bool:
        try:
            self._conn.execute(
                """
                INSERT INTO processed_invoices (invoice_key, status, updated_at)
                VALUES (?, ?, ?)
                """,
                (invoice_key, "received", datetime.now(UTC).isoformat()),
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
        self._conn.execute(
            """
            UPDATE processed_invoices
            SET status = ?, last_error = ?, attempts = attempts + 1, updated_at = ?
            WHERE invoice_key = ?
            """,
            ("failed", error, datetime.now(UTC).isoformat(), invoice_key),
        )
        self._conn.commit()
