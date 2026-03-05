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


@dataclass
class IngestionResult:
    """Result of the ingestion phase."""
    
    messages_processed: int
    files_stored: int
    files_quarantined: int
    errors: List[str]


class EmailIngestionUseCase:
    """Phase 1: Ingest emails and store attachments safely."""

    def __init__(
        self,
        email_processor: EmailProcessor,
        file_storage: FileStorageService,
    ):
        self._email_processor = email_processor
        self._file_storage = file_storage

    def ingest_new_emails(self, dry_run: bool = False) -> IngestionResult:
        """Fetch emails and store attachments, ready for async parsing."""
        messages = self._email_processor.fetch_new_messages()

        result = IngestionResult(
            messages_processed=len(messages),
            files_stored=0,
            files_quarantined=0,
            errors=[],
        )

        for message in messages:
            try:
                self._ingest_single_message(message, result, dry_run)
                
                if not dry_run:
                    try:
                        self._email_processor.mark_as_processed(message.message_id)
                    except Exception as e:
                        result.errors.append(
                            f"Failed to mark message as processed: {message.message_id}: {e}"
                        )
            except Exception as exc:
                result.errors.append(f"Error ingesting message {message.message_id}: {str(exc)}")

        return result

    def _ingest_single_message(
        self,
        message: EmailMessage,
        result: IngestionResult,
        dry_run: bool,
    ) -> None:
        """Store all attachments from one message."""
        for attachment in message.attachments:
            if dry_run:
                # Just validate, don't store
                result_type, _ = (FileStorageResult.SAFE_STORAGE, "dry-run-path")
            else:
                result_type, file_path = self._file_storage.store_attachment(attachment)

            if result_type == FileStorageResult.QUARANTINE:
                result.files_quarantined += 1
            elif result_type == FileStorageResult.REJECTED:
                result.errors.append(f"File rejected: {attachment.filename}")
            elif result_type == FileStorageResult.SAFE_STORAGE:
                result.files_stored += 1


class InvoiceParsingUseCase:
    """Phase 2: Parse stored files asynchronously."""

    def __init__(
        self,
        document_parser: DocumentParser | Iterable[DocumentParser],
        repository: ProcessedInvoiceRepository,
    ):
        if isinstance(document_parser, (list, tuple)):
            self._document_parsers = list(document_parser)
        else:
            self._document_parsers = [document_parser]
        self._repository = repository

    def parse_safe_files(self, file_paths: List[Path]) -> ProcessingResult:
        """Parse a batch of files from safe storage."""
        result = ProcessingResult(
            messages_processed=0,  # Not applicable for this phase
            invoices_found=0,
            invoices_uploaded=0,
            files_quarantined=0,
            errors=[],
        )

        for file_path in file_paths:
            try:
                self._parse_single_file(file_path, result)
            except Exception as exc:
                result.errors.append(f"Error parsing file {file_path}: {str(exc)}")

        return result

    def _parse_single_file(self, file_path: Path, result: ProcessingResult) -> None:
        """Parse one file and save results."""
        parser = self._select_parser(file_path)
        if not parser:
            file_suffix = file_path.suffix
            result.errors.append(
                f"No parser available for file type: {file_suffix} ({file_path.name})"
            )
            return

        parse_result = parser.parse_invoice(file_path)
        self._write_parse_result(file_path, parse_result)

        if parse_result.success and parse_result.invoice:
            result.invoices_found += 1

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

    def _select_parser(self, file_path: Path) -> DocumentParser | None:
        """Pick the first parser that can handle the file."""
        for parser in self._document_parsers:
            try:
                if parser.can_parse(file_path):
                    return parser
            except Exception:
                continue
        return None


class InvoiceExportUseCase:
    """Phase 3: Export/integrate parsed invoices."""

    def __init__(self, repository: ProcessedInvoiceRepository):
        self._repository = repository

    def export_parsed_invoices(self, parsed_files: List[Path], dry_run: bool = False) -> ProcessingResult:
        """Export parsed invoices, handling idempotency."""
        result = ProcessingResult(
            messages_processed=0,
            invoices_found=0,
            invoices_uploaded=0,
            files_quarantined=0,
            errors=[],
        )

        for file_path in parsed_files:
            try:
                parsed_json_path = file_path.with_suffix(".parsed.json")
                if not parsed_json_path.exists():
                    continue

                with open(parsed_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not data.get("success") or not data.get("invoice"):
                    continue

                invoice_data = data["invoice"]
                invoice_key = invoice_data["invoice_key"]
                
                result.invoices_found += 1

                if self._repository.claim(invoice_key):
                    if not dry_run:
                        # Placeholder for external integration
                        # await external_api.upload_invoice(invoice_data)
                        pass
                    
                    result.invoices_uploaded += 1
                    
                    if not dry_run:
                        self._repository.mark_done(invoice_key)

            except Exception as exc:
                result.errors.append(f"Error exporting {file_path}: {str(exc)}")

        return result


class EmailProcessingUseCase:
    """Legacy unified processor for backward compatibility."""

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

        # Delegate to the new separated use cases
        self._ingestion = EmailIngestionUseCase(email_processor, file_storage)
        self._parsing = InvoiceParsingUseCase(document_parser, repository)
        self._export = InvoiceExportUseCase(repository)

    def process_new_emails(self, dry_run: bool = False) -> ProcessingResult:
        """Unified processing for backward compatibility."""
        result = ProcessingResult(
            messages_processed=0,
            invoices_found=0,
            invoices_uploaded=0,
            files_quarantined=0,
            errors=[],
        )

        messages = self._email_processor.fetch_new_messages()
        result.messages_processed = len(messages)

        for message in messages:
            for attachment in message.attachments:
                try:
                    storage_result, file_path = self._file_storage.store_attachment(attachment)
                except Exception as exc:
                    result.errors.append(str(exc))
                    continue

                if storage_result == FileStorageResult.QUARANTINE:
                    result.files_quarantined += 1
                    continue

                if storage_result == FileStorageResult.REJECTED:
                    result.errors.append(f"File rejected: {attachment.filename}")
                    continue

                parsed_invoice = self._parse_invoice_with_compatible_parser(Path(file_path))
                if not parsed_invoice:
                    continue

                result.invoices_found += 1
                if self._repository.claim(parsed_invoice.invoice_key):
                    result.invoices_uploaded += 1
                    if not dry_run:
                        self._repository.mark_done(parsed_invoice.invoice_key)

            if not dry_run:
                try:
                    self._email_processor.mark_as_processed(message.message_id)
                except Exception as exc:
                    result.errors.append(
                        f"Failed to mark message as processed: {message.message_id}: {exc}"
                    )

        return result

    def _parse_invoice_with_compatible_parser(self, file_path: Path) -> Invoice | None:
        """Parse invoice while supporting both legacy and capability-based parsers."""
        for parser in self._document_parsers:
            try:
                can_parse = getattr(parser, "can_parse", None)
                if callable(can_parse) and not can_parse(file_path):
                    continue
                parse_result = parser.parse_invoice(file_path)
            except Exception:
                continue

            if parse_result and parse_result.success and parse_result.invoice:
                return parse_result.invoice

        return None


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
