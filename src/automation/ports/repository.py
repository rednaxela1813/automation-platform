from __future__ import annotations

from abc import ABC, abstractmethod


class ProcessedInvoiceRepository(ABC):
    @abstractmethod
    def claim(self, invoice_key: str) -> bool:
        """
        Try to claim invoice for processing.
        Returns True if successfully claimed.
        Returns False if already processed.
        """

    @abstractmethod
    def mark_done(self, invoice_key: str) -> None: ...

    @abstractmethod
    def mark_failed(self, invoice_key: str, error: str) -> None: ...
