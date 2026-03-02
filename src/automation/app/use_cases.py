# automation-platform/src/automation/app/use_cases.py

"""Application use cases for email and invoice processing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List

from automation.domain.models import Invoice
from automation.ports.document_parser import DocumentParser, ParseResult
from automation.ports.email import EmailMessage, EmailProcessor
from automation.ports.file_storage import FileStorageResult, FileStorageService
from automation.ports.repository import ProcessedInvoiceRepository


@dataclass
class ProcessingResult:
    """Result summary for one email processing run."""

    messages_processed: int
    invoices_found: int
    invoices_uploaded: int
    files_quarantined: int
    errors: List[str]


class EmailProcessingUseCase:
    """Process new emails, parse invoices, and persist processing status."""

    def __init__(
        self,
        email_processor: EmailProcessor,
        repository: ProcessedInvoiceRepository,
        document_parser: DocumentParser | Iterable[DocumentParser],
        file_storage: FileStorageService,
    ):
        self._email_processor = email_processor
        self._repository = repository
        if isinstance(document_parser, (list, tuple)):
            self._document_parsers = list(document_parser)
        else:
            self._document_parsers = [document_parser]
        self._file_storage = file_storage

    def process_new_emails(self, dry_run: bool = False) -> ProcessingResult:
        """Fetch and process all currently available new emails."""
        messages = self._email_processor.fetch_new_messages()

        result = ProcessingResult(
            messages_processed=len(messages),
            invoices_found=0,
            invoices_uploaded=0,
            files_quarantined=0,
            errors=[],
        )

        for message in messages:
            try:
                self._process_single_message(message, result, dry_run)
                # Mark message as processed only after handling attachments.
                try:
                    self._email_processor.mark_as_processed(message.message_id)
                except Exception:
                    result.errors.append(
                        f"Failed to mark message as processed: {message.message_id}"
                    )
            except Exception as exc:
                result.errors.append(f"Error processing message {message.message_id}: {str(exc)}")

        return result

    def _process_single_message(
        self,
        message: EmailMessage,
        result: ProcessingResult,
        dry_run: bool,
    ) -> None:
        """Handle all attachments from one message."""
        for attachment in message.attachments:
            result_type, file_path = self._file_storage.store_attachment(attachment)

            if result_type == FileStorageResult.QUARANTINE:
                result.files_quarantined += 1
                continue
            if result_type == FileStorageResult.REJECTED:
                result.errors.append(f"File rejected: {attachment.filename}")
                continue

            parser = self._select_parser(file_path)
            if not parser:
                file_suffix = Path(file_path).suffix
                result.errors.append(
                    f"No parser available for file type: "
                    f"{file_suffix} ({attachment.filename})"
                )
                continue

            parse_result = parser.parse_invoice(Path(file_path))
            self._write_parse_result(Path(file_path), parse_result)

            if parse_result.success and parse_result.invoice:
                result.invoices_found += 1

                if self._repository.claim(parse_result.invoice.invoice_key):
                    if not dry_run:
                        # Placeholder for outbound upload/integration call.
                        pass
                    result.invoices_uploaded += 1

                    if not dry_run:
                        self._repository.mark_done(parse_result.invoice.invoice_key)

    def _write_parse_result(self, file_path: Path, parse_result: ParseResult) -> None:
        """Persist parser output near the source file for traceability."""
        try:
            invoice = parse_result.invoice
            payload: dict[str, Any] = {
                "parsed_at": datetime.now().isoformat(),
                "success": parse_result.success,
                "errors": parse_result.errors,
                "metadata": parse_result.metadata,
                "invoice": None,
            }

            if invoice:
                payload["invoice"] = {
                    "partner_id": invoice.partner_id,
                    "invoice_number": invoice.invoice_number,
                    "invoice_date": invoice.invoice_date.isoformat(),
                    "amount": str(invoice.amount),
                    "currency": invoice.currency,
                    "source_message_id": invoice.source_message_id,
                    "invoice_key": invoice.invoice_key,
                }

            parsed_path = file_path.with_suffix(".parsed.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            # Parse-result persistence must never break the main processing flow.
            return

    def _select_parser(self, file_path: str) -> DocumentParser | None:
        """Pick the first parser that can handle the file."""
        path = Path(file_path)
        for parser in self._document_parsers:
            try:
                if parser.can_parse(path):
                    return parser
            except Exception:
                continue
        return None

    def _is_valid_attachment(self, attachment) -> bool:
        """Legacy placeholder kept for compatibility."""
        return True


class InvoiceValidationUseCase:
    """Simple invoice validation use case."""

    def __init__(self, repository: ProcessedInvoiceRepository):
        self._repository = repository

    def validate_invoice_data(self, invoice: Invoice) -> bool:
        """Validate minimal invoice business constraints."""
        if invoice.amount <= 0:
            return False
        if not invoice.partner_id:
            return False
        return True
