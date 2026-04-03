from __future__ import annotations

from automation.adapters.repository_sqlalchemy import SqlAlchemyProcessedInvoiceRepository
from automation.config.settings import settings
from automation.ports.repository import ProcessedInvoiceRepository


def create_processed_invoice_repository(
    database_url: str | None = None,
) -> ProcessedInvoiceRepository:
    resolved_url = database_url or settings.database_url
    return SqlAlchemyProcessedInvoiceRepository(resolved_url)
