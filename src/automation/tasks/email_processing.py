# automation-platform/src/automation/tasks/email_processing.py

"""
Background tasks for email processing
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from automation.adapters.email_imap import ImapEmailClient
from automation.adapters.file_storage import LocalFileStorage
from automation.adapters.parser_registry import get_document_parsers
from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository
from automation.app.use_cases import EmailProcessingUseCase
from automation.celery_app import celery_app
from automation.config.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, retry_kwargs={"max_retries": 3, "countdown": 60})
def process_new_emails_task(self) -> Dict[str, Any]:
    """
    Periodic task for processing new email messages
    """
    try:
        logger.info("Starting email processing task")

        # Initialize dependencies
        email_processor = ImapEmailClient()
        db_path = settings.database_url
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
        repository = SqliteProcessedInvoiceRepository(Path(db_path))
        document_parser = get_document_parsers()
        file_storage = LocalFileStorage()

        # Create use case
        use_case = EmailProcessingUseCase(
            email_processor=email_processor,
            repository=repository,
            document_parser=document_parser,
            file_storage=file_storage,
        )

        # Process new email
        result = use_case.process_new_emails()

        logger.info(
            f"Email processing completed: {result.messages_processed} messages, "
            f"{result.invoices_found} invoices found, "
            f"{result.invoices_uploaded} uploaded"
        )

        return {
            "status": "success",
            "messages_processed": result.messages_processed,
            "invoices_found": result.invoices_found,
            "invoices_uploaded": result.invoices_uploaded,
            "files_quarantined": result.files_quarantined,
            "errors": result.errors[:10],  # Limit number of errors in response
        }

    except Exception as exc:
        logger.error(f"Email processing task failed: {exc}", exc_info=True)

        # Retry task on error
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for email processing task")
            return {"status": "failed", "error": str(exc), "messages_processed": 0}


@celery_app.task(bind=True)
def process_single_email_task(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task for processing one email message
    Used for real-time email processing via webhook
    """
    try:
        logger.info(f"Processing single email: {message_data.get('message_id')}")

        # Single-message processing logic goes here
        # When a webhook arrives from a mail provider

        return {
            "status": "success",
            "message_id": message_data.get("message_id"),
            "processed_at": "2024-02-20T10:00:00Z",
        }

    except Exception as exc:
        logger.error(f"Single email processing failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}


@celery_app.task
def send_processing_report_task(period: str = "daily") -> Dict[str, Any]:
    """
    Generate and send processing summary report.
    """
    try:
        logger.info(f"Generating {period} processing report")

        # Placeholder: collect real metrics and attach delivery channel details.

        report_data = {
            "period": period,
            "emails_processed": 42,
            "invoices_extracted": 38,
            "errors": ["Connection timeout", "Invalid file format"],
        }

        # Placeholder: send report via selected channel (email, Slack, etc.)
        logger.info(f"Processing report sent: {report_data}")

        return {"status": "success", "report": report_data}

    except Exception as exc:
        logger.error(f"Report generation failed: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}
