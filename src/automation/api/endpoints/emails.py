"""Email processing API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from automation.api.dependencies import get_settings
from automation.config.settings import Settings

router = APIRouter()
logger = logging.getLogger(__name__)


LAST_PROCESSING_STATUS: dict[str, object] = {
    "status": "idle",
    "message": "No processing has been run yet",
    "processed_at": datetime.now(),
    "emails_processed": 0,
    "files_processed": 0,
    "files_quarantined": 0,
    "emails_without_attachments": 0,
    "emails_marked_processed": 0,
    "parser_failures": 0,
    "invoices_found": 0,
    "invoices_uploaded": 0,
}


class ProcessingStatusResponse(BaseModel):
    status: str
    message: str
    processed_at: datetime
    emails_processed: int = 0
    files_processed: int = 0
    files_quarantined: int = 0
    emails_without_attachments: int = 0
    emails_marked_processed: int = 0
    parser_failures: int = 0
    invoices_found: int = 0
    invoices_uploaded: int = 0


class EmailProcessingRequest(BaseModel):
    force_reprocess: bool = False
    dry_run: bool = False


@router.post("/emails/process", response_model=ProcessingStatusResponse)
async def trigger_email_processing(
    request: EmailProcessingRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    """Trigger asynchronous email processing."""
    try:
        background_tasks.add_task(process_emails_task, request.force_reprocess, request.dry_run)
        return ProcessingStatusResponse(
            status="started",
            message="Email processing started in background",
            processed_at=datetime.now(),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(exc)}")


@router.get("/emails/status", response_model=ProcessingStatusResponse)
async def get_processing_status():
    """Return current processing status."""
    return ProcessingStatusResponse(**LAST_PROCESSING_STATUS)


async def process_emails_task(force_reprocess: bool = False, dry_run: bool = False):
    """Run one email processing cycle in background."""
    LAST_PROCESSING_STATUS.update(
        {
            "status": "running",
            "message": "Email processing in progress",
            "processed_at": datetime.now(),
            "emails_processed": 0,
            "files_processed": 0,
            "files_quarantined": 0,
            "emails_without_attachments": 0,
            "emails_marked_processed": 0,
            "parser_failures": 0,
            "invoices_found": 0,
            "invoices_uploaded": 0,
        }
    )
    logger.info(
        "Starting email processing task: force_reprocess=%s dry_run=%s",
        force_reprocess,
        dry_run,
    )

    try:
        from automation.adapters.email_imap import ImapEmailClient
        from automation.adapters.file_storage import LocalFileStorage
        from automation.adapters.parser_registry import get_document_parsers
        from automation.adapters.repository_factory import create_processed_invoice_repository
        from automation.app.use_cases import EmailProcessingUseCase
        from automation.config.settings import settings

        email_client = ImapEmailClient()
        repository = create_processed_invoice_repository(settings.database_url)

        document_parsers = get_document_parsers()
        file_storage = LocalFileStorage()

        use_case = EmailProcessingUseCase(
            email_processor=email_client,
            repository=repository,
            document_parser=document_parsers,
            file_storage=file_storage,
        )

        result = use_case.process_new_emails(
            dry_run=dry_run,
            force_reprocess=force_reprocess,
        )

        LAST_PROCESSING_STATUS.update(
            {
                "status": "completed",
                "message": "Email processing completed",
                "processed_at": datetime.now(),
                "emails_processed": result.messages_processed,
                "files_processed": result.files_processed,
                "files_quarantined": result.files_quarantined,
                "emails_without_attachments": result.emails_without_attachments,
                "emails_marked_processed": result.emails_marked_processed,
                "parser_failures": result.parser_failures,
                "invoices_found": result.invoices_found,
                "invoices_uploaded": result.invoices_uploaded,
            }
        )

        logger.info(
            "Email processing completed: %s messages, %s files stored, %s invoices found, "
            "%s uploaded, %s quarantined, %s parser failures, %s emails without attachments, "
            "%s emails marked as processed",
            result.messages_processed,
            result.files_processed,
            result.invoices_found,
            result.invoices_uploaded,
            result.files_quarantined,
            result.parser_failures,
            result.emails_without_attachments,
            result.emails_marked_processed,
        )

    except Exception as exc:
        LAST_PROCESSING_STATUS.update(
            {
                "status": "failed",
                "message": f"Email processing failed: {exc}",
                "processed_at": datetime.now(),
            }
        )
        logger.exception("Email processing failed: %s", str(exc))
