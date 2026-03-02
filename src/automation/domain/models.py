# src/automation/domain/models.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class InvoiceStatus(str, Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    VALIDATED = "validated"
    UPLOADED = "uploaded"
    DONE = "done"
    FAILED = "failed"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class Invoice:
    partner_id: str
    invoice_number: str
    invoice_date: date
    amount: Decimal
    currency: str
    source_message_id: str

    @property
    def invoice_key(self) -> str:
        """
        Stable idempotency key.
        Does NOT include amount to allow corrections.
        """
        return f"{self.partner_id}:{self.invoice_number}:{self.invoice_date.isoformat()}"
