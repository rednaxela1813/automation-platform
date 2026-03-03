"""Email processing API endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from automation.api.dependencies import get_settings
from automation.config.settings import Settings

router = APIRouter()


class ProcessingStatusResponse(BaseModel):
    status: str
    message: str
    processed_at: datetime
    emails_processed: int = 0
    files_processed: int = 0
    files_quarantined: int = 0


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
    return ProcessingStatusResponse(
        status="idle",
        message="No active processing",
        processed_at=datetime.now(),
    )


async def process_emails_task(force_reprocess: bool = False, dry_run: bool = False):
    """Run one email processing cycle in background."""
    print(f"🚀 Starting email processing: force={force_reprocess}, dry_run={dry_run}")

    try:
        from automation.adapters.email_imap import ImapEmailClient
        from automation.adapters.file_storage import LocalFileStorage
        from automation.adapters.parser_registry import get_document_parsers
        from automation.adapters.repository_sqlite import SqliteProcessedInvoiceRepository
        from automation.app.use_cases import EmailProcessingUseCase
        from automation.config.settings import settings

        email_client = ImapEmailClient()

        db_path = settings.database_url
        if db_path.startswith("sqlite:///"):
            db_path = db_path.replace("sqlite:///", "")
        repository = SqliteProcessedInvoiceRepository(db_path)

        document_parsers = get_document_parsers()
        file_storage = LocalFileStorage()

        use_case = EmailProcessingUseCase(
            email_processor=email_client,
            repository=repository,
            document_parser=document_parsers,
            file_storage=file_storage,
        )

        result = use_case.process_new_emails(dry_run=dry_run)

        print(
            f"✅ Email processing completed: {result.messages_processed} messages, "
            f"{result.invoices_found} invoices found, {result.invoices_uploaded} uploaded, "
            f"{result.files_quarantined} quarantined"
        )

    except Exception as exc:
        print(f"❌ Email processing failed: {str(exc)}")
        import traceback

        traceback.print_exc()
