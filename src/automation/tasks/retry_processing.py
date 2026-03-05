"""Celery task for retry failed invoice processing."""

from __future__ import annotations

import logging
from pathlib import Path

from automation.adapters.file_storage import LocalFileStorage
from automation.adapters.parser_registry import ParserRegistry
from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository
from automation.app.use_cases import InvoiceParsingUseCase, InvoiceExportUseCase
from automation.celery_app import celery
from automation.config.settings import settings

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3)
def retry_failed_invoices_task(self):
    """Retry processing of failed invoices that are eligible for retry."""
    try:
        # Initialize dependencies
        repository = SqliteProcessedInvoiceRepository(Path("emails.db"))
        parser_registry = ParserRegistry()
        file_storage = LocalFileStorage()
        
        parsing_use_case = InvoiceParsingUseCase(parser_registry.get_parsers(), repository)
        export_use_case = InvoiceExportUseCase(repository)

        # Get items eligible for retry
        retryable_keys = repository.get_retryable_items()
        
        if not retryable_keys:
            logger.info("No items eligible for retry")
            return {"retried": 0, "success": 0, "failed": 0}

        logger.info(f"Found {len(retryable_keys)} items eligible for retry")

        success_count = 0
        failed_count = 0

        for invoice_key in retryable_keys:
            try:
                # Reset status to allow retry
                if not repository.reset_for_retry(invoice_key):
                    logger.warning(f"Could not reset status for {invoice_key}")
                    continue

                # Find corresponding file (simplified - assumes invoice_key maps to filename)
                # In production, you'd want a more robust file lookup mechanism
                safe_files = [f for f in file_storage.get_safe_files() if invoice_key in f.stem]
                
                if not safe_files:
                    logger.warning(f"No safe file found for invoice_key: {invoice_key}")
                    repository.mark_failed(invoice_key, "Source file not found during retry")
                    failed_count += 1
                    continue

                # Re-parse and export
                parse_result = parsing_use_case.parse_safe_files([safe_files[0]])
                export_result = export_use_case.export_parsed_invoices([safe_files[0]])

                if export_result.invoices_uploaded > 0:
                    success_count += 1
                    logger.info(f"Successfully retried invoice: {invoice_key}")
                else:
                    failed_count += 1
                    error_msg = "; ".join(export_result.errors) if export_result.errors else "Unknown retry failure"
                    repository.mark_failed(invoice_key, f"Retry failed: {error_msg}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error during retry of {invoice_key}: {e}")
                repository.mark_failed(invoice_key, f"Retry exception: {str(e)}")

        return {
            "retried": len(retryable_keys),
            "success": success_count,
            "failed": failed_count
        }

    except Exception as e:
        logger.error(f"Retry task failed: {e}")
        raise self.retry(exc=e, countdown=60)


@celery.task
def cleanup_old_records_task():
    """Cleanup old completed records from the database."""
    try:
        repository = SqliteProcessedInvoiceRepository(Path("emails.db"))
        deleted_count = repository.cleanup_old_records(days_old=90)
        
        logger.info(f"Cleaned up {deleted_count} old records")
        return {"deleted_records": deleted_count}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        raise


@celery.task
def get_processing_status_task():
    """Get current processing status summary for monitoring."""
    try:
        repository = SqliteProcessedInvoiceRepository(Path("emails.db"))
        status_summary = repository.get_status_summary()
        
        logger.info(f"Processing status: {status_summary}")
        return status_summary
        
    except Exception as e:
        logger.error(f"Status check task failed: {e}")
        raise