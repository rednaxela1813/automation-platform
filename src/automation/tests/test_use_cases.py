"""Use case tests."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest

from automation.app.use_cases import (
    EmailIngestionUseCase,
    EmailProcessingUseCase,
    InvoiceExportUseCase,
    InvoiceParsingUseCase,
    InvoiceValidationUseCase,
    ProcessingResult,
)
from automation.ports.document_parser import ParseResult
from automation.domain.models import Invoice
from automation.ports.email import EmailAttachment, EmailMessage
from automation.ports.file_storage import FileStorageResult


@pytest.fixture
def mock_dependencies():
    """Create mock dependency objects"""
    return {
        "email_processor": Mock(),
        "repository": Mock(),
        "document_parser": Mock(),
        "file_storage": Mock(),
    }


@pytest.fixture
def sample_invoice():
    """Create test invoice"""
    return Invoice(
        partner_id="test_partner",
        invoice_number="INV-2024-001",
        invoice_date=date(2024, 2, 20),
        amount=Decimal("150.00"),
        currency="EUR",
        source_message_id="test-message-id",
    )


@pytest.fixture
def sample_email_message():
    """Create test email with attachment"""
    attachment = EmailAttachment(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"fake pdf content",
        size=1024,
    )

    return EmailMessage(
        message_id="test-msg-1",
        subject="Invoice from supplier",
        sender="supplier@example.com",
        received_date="2024-02-20T10:00:00Z",
        body="Please find attached invoice",
        attachments=[attachment],
    )


class TestEmailProcessingUseCase:
    """Tests for EmailProcessingUseCase"""

    def test_process_new_emails_success(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        """Test successful email processing"""

        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)

        # Setup mocks
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result

        mock_dependencies["repository"].claim.return_value = True

        # Act
        result = use_case.process_new_emails()

        # Assert
        assert isinstance(result, ProcessingResult)
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 1
        assert len(result.errors) == 0

        # Verify mocks were called
        mock_dependencies["email_processor"].fetch_new_messages.assert_called_once()
        mock_dependencies["repository"].claim.assert_called_once_with(sample_invoice.invoice_key)
        mock_dependencies["repository"].mark_done.assert_called_once_with(
            sample_invoice.invoice_key
        )

    def test_process_new_emails_duplicate_invoice(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        """Test duplicate invoice handling"""

        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)

        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result

        # Simulate already processed invoice
        mock_dependencies["repository"].claim.return_value = False

        # Act
        result = use_case.process_new_emails()

        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 0  # Duplicate not uploaded

        # mark_done should not be called for duplicates
        mock_dependencies["repository"].mark_done.assert_not_called()

    def test_process_new_emails_parsing_failure(self, mock_dependencies, sample_email_message):
        """Test parsing error handling"""

        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)

        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        # Simulate parsing error
        parse_result = Mock()
        parse_result.success = False
        parse_result.invoice = None
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result

        # Act
        result = use_case.process_new_emails()

        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 0
        assert result.invoices_uploaded == 0

        # repository.claim should not be called on parsing error
        mock_dependencies["repository"].claim.assert_not_called()

    def test_process_new_emails_dry_run(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        """Test dry-run mode"""

        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)

        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]

        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result

        mock_dependencies["repository"].claim.return_value = True
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        # Act
        result = use_case.process_new_emails(dry_run=True)

        # Assert
        assert result.messages_processed == 1
        assert result.invoices_found == 1
        assert result.invoices_uploaded == 1  # Counted as "uploaded" in dry run

        # No real operations should run in dry-run mode
        mock_dependencies["file_storage"].store_attachment.assert_called_once()
        mock_dependencies["repository"].mark_done.assert_not_called()

    def test_process_new_emails_exception_handling(self, mock_dependencies, sample_email_message):
        """Test exception handling"""

        # Arrange
        use_case = EmailProcessingUseCase(**mock_dependencies)

        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]

        # Simulate processing exception
        mock_dependencies["file_storage"].store_attachment.side_effect = Exception("Storage error")

        # Act
        result = use_case.process_new_emails()

        # Assert
        assert result.messages_processed == 1
        assert len(result.errors) == 1
        assert "Storage error" in result.errors[0]
        assert result.invoices_uploaded == 0

    def test_process_new_emails_continues_after_repository_error(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        """One broken message must not abort the whole batch."""

        second_message = EmailMessage(
            message_id="test-msg-2",
            subject="Second invoice",
            sender="supplier@example.com",
            received_date="2024-02-20T10:05:00Z",
            body="Please find attached invoice",
            attachments=sample_email_message.attachments,
        )

        use_case = EmailProcessingUseCase(**mock_dependencies)
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message,
            second_message,
        ]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result
        mock_dependencies["repository"].claim.side_effect = [
            Exception("db failed"),
            True,
        ]

        result = use_case.process_new_emails()

        assert result.messages_processed == 2
        assert result.invoices_found == 2
        assert result.invoices_uploaded == 1
        assert any("Failed to persist invoice" in error for error in result.errors)
        mock_dependencies["email_processor"].mark_as_processed.assert_called_once_with("test-msg-2")

    def test_process_new_emails_does_not_mark_message_processed_on_repository_error(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        """A failed message should remain unread/unprocessed for retry."""

        use_case = EmailProcessingUseCase(**mock_dependencies)
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [
            sample_email_message
        ]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )

        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result
        mock_dependencies["repository"].claim.side_effect = Exception("db failed")

        result = use_case.process_new_emails()

        assert result.invoices_uploaded == 0
        assert any("Failed to persist invoice" in error for error in result.errors)
        mock_dependencies["email_processor"].mark_as_processed.assert_not_called()

    def test_process_new_emails_passes_force_reprocess_to_email_processor(
        self, mock_dependencies, sample_email_message
    ):
        use_case = EmailProcessingUseCase(**mock_dependencies)
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.QUARANTINE,
            "/path/to/file.pdf",
        )

        use_case.process_new_emails(force_reprocess=True)

        mock_dependencies["email_processor"].fetch_new_messages.assert_called_once_with(
            force_reprocess=True
        )

    def test_process_new_emails_records_mark_done_failure_but_continues(
        self, mock_dependencies, sample_email_message, sample_invoice
    ):
        use_case = EmailProcessingUseCase(**mock_dependencies)
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.SAFE_STORAGE,
            "/path/to/file.pdf",
        )
        parse_result = Mock()
        parse_result.success = True
        parse_result.invoice = sample_invoice
        mock_dependencies["document_parser"].parse_invoice.return_value = parse_result
        mock_dependencies["repository"].claim.return_value = True
        mock_dependencies["repository"].mark_done.side_effect = RuntimeError("finalize failed")

        result = use_case.process_new_emails()

        assert result.invoices_uploaded == 1
        assert any("Failed to finalize invoice" in error for error in result.errors)
        mock_dependencies["email_processor"].mark_as_processed.assert_not_called()


class TestEmailIngestionUseCase:
    def test_ingest_new_emails_counts_stored_and_quarantined(
        self, mock_dependencies, sample_email_message
    ):
        use_case = EmailIngestionUseCase(
            email_processor=mock_dependencies["email_processor"],
            file_storage=mock_dependencies["file_storage"],
        )
        rejected_attachment = EmailAttachment(
            filename="bad.exe",
            content_type="application/octet-stream",
            content=b"MZ",
            size=2,
        )
        message = EmailMessage(
            message_id="msg-1",
            subject="Mixed attachments",
            sender="sender@example.com",
            received_date="2024-02-20T10:00:00Z",
            body="Body",
            attachments=[sample_email_message.attachments[0], rejected_attachment],
        )
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [message]
        mock_dependencies["file_storage"].store_attachment.side_effect = [
            (FileStorageResult.SAFE_STORAGE, "/tmp/ok.pdf"),
            (FileStorageResult.QUARANTINE, "/tmp/bad.exe"),
        ]

        result = use_case.ingest_new_emails()

        assert result.messages_processed == 1
        assert result.files_stored == 1
        assert result.files_quarantined == 1
        assert result.errors == []
        mock_dependencies["email_processor"].mark_as_processed.assert_called_once_with("msg-1")

    def test_ingest_new_emails_dry_run_does_not_store_or_mark(
        self, mock_dependencies, sample_email_message
    ):
        use_case = EmailIngestionUseCase(
            email_processor=mock_dependencies["email_processor"],
            file_storage=mock_dependencies["file_storage"],
        )
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [sample_email_message]

        result = use_case.ingest_new_emails(dry_run=True)

        assert result.files_stored == 1
        mock_dependencies["file_storage"].store_attachment.assert_not_called()
        mock_dependencies["email_processor"].mark_as_processed.assert_not_called()

    def test_ingest_new_emails_records_rejected_files(
        self, mock_dependencies, sample_email_message
    ):
        use_case = EmailIngestionUseCase(
            email_processor=mock_dependencies["email_processor"],
            file_storage=mock_dependencies["file_storage"],
        )
        mock_dependencies["email_processor"].fetch_new_messages.return_value = [sample_email_message]
        mock_dependencies["file_storage"].store_attachment.return_value = (
            FileStorageResult.REJECTED,
            "bad",
        )

        result = use_case.ingest_new_emails()

        assert result.files_stored == 0
        assert result.files_quarantined == 0
        assert result.errors == ["File rejected: invoice.pdf"]


class TestInvoiceParsingUseCase:
    def test_parse_safe_files_writes_parsed_json_for_success(self, sample_invoice, tmp_path: Path):
        parser = Mock()
        parser.can_parse.return_value = True
        parser.parse_invoice.return_value = ParseResult(
            success=True,
            invoice=sample_invoice,
            errors=[],
            metadata={"source": "test"},
        )
        use_case = InvoiceParsingUseCase(parser, Mock())
        file_path = tmp_path / "invoice.pdf"
        file_path.write_bytes(b"pdf")

        result = use_case.parse_safe_files([file_path])

        assert result.invoices_found == 1
        parsed_path = file_path.with_suffix(".parsed.json")
        payload = json.loads(parsed_path.read_text(encoding="utf-8"))
        assert payload["success"] is True
        assert payload["invoice"]["invoice_key"] == sample_invoice.invoice_key

    def test_parse_safe_files_reports_missing_parser(self, tmp_path: Path):
        parser = Mock()
        parser.can_parse.return_value = False
        use_case = InvoiceParsingUseCase(parser, Mock())
        file_path = tmp_path / "invoice.unknown"
        file_path.write_text("x", encoding="utf-8")

        result = use_case.parse_safe_files([file_path])

        assert result.invoices_found == 0
        assert result.errors == ["No parser available for file type: .unknown (invoice.unknown)"]

    def test_parse_safe_files_continues_when_parser_selection_raises(self, sample_invoice, tmp_path: Path):
        broken_parser = Mock()
        broken_parser.can_parse.side_effect = RuntimeError("broken")
        good_parser = Mock()
        good_parser.can_parse.return_value = True
        good_parser.parse_invoice.return_value = ParseResult(
            success=True,
            invoice=sample_invoice,
            errors=[],
            metadata={},
        )
        use_case = InvoiceParsingUseCase([broken_parser, good_parser], Mock())
        file_path = tmp_path / "invoice.pdf"
        file_path.write_bytes(b"pdf")

        result = use_case.parse_safe_files([file_path])

        assert result.invoices_found == 1


class TestInvoiceExportUseCase:
    def test_export_parsed_invoices_claims_and_marks_done(self, sample_invoice, tmp_path: Path):
        repository = Mock()
        repository.claim.return_value = True
        use_case = InvoiceExportUseCase(repository)
        source_file = tmp_path / "invoice.pdf"
        source_file.write_bytes(b"pdf")
        parsed_file = source_file.with_suffix(".parsed.json")
        parsed_file.write_text(
            json.dumps(
                {
                    "success": True,
                    "invoice": {
                        "invoice_key": sample_invoice.invoice_key,
                    },
                }
            ),
            encoding="utf-8",
        )

        result = use_case.export_parsed_invoices([source_file])

        assert result.invoices_found == 1
        assert result.invoices_uploaded == 1
        repository.claim.assert_called_once_with(sample_invoice.invoice_key)
        repository.mark_done.assert_called_once_with(sample_invoice.invoice_key)

    def test_export_parsed_invoices_skips_missing_or_unsuccessful_files(self, tmp_path: Path):
        repository = Mock()
        use_case = InvoiceExportUseCase(repository)
        source_file = tmp_path / "invoice.pdf"
        source_file.write_bytes(b"pdf")
        parsed_file = source_file.with_suffix(".parsed.json")
        parsed_file.write_text(json.dumps({"success": False, "invoice": None}), encoding="utf-8")

        result = use_case.export_parsed_invoices([source_file, tmp_path / "missing.pdf"])

        assert result.invoices_found == 0
        assert result.invoices_uploaded == 0
        repository.claim.assert_not_called()

    def test_export_parsed_invoices_dry_run_does_not_mark_done(self, sample_invoice, tmp_path: Path):
        repository = Mock()
        repository.claim.return_value = True
        use_case = InvoiceExportUseCase(repository)
        source_file = tmp_path / "invoice.pdf"
        source_file.write_bytes(b"pdf")
        source_file.with_suffix(".parsed.json").write_text(
            json.dumps(
                {"success": True, "invoice": {"invoice_key": sample_invoice.invoice_key}}
            ),
            encoding="utf-8",
        )

        result = use_case.export_parsed_invoices([source_file], dry_run=True)

        assert result.invoices_uploaded == 1
        repository.mark_done.assert_not_called()


class TestInvoiceValidationUseCase:
    def test_validate_invoice_data_checks_amount_and_partner(self, sample_invoice):
        use_case = InvoiceValidationUseCase(Mock())

        assert use_case.validate_invoice_data(sample_invoice) is True
        assert (
            use_case.validate_invoice_data(
                Invoice(
                    partner_id="",
                    invoice_number="INV-1",
                    invoice_date=sample_invoice.invoice_date,
                    amount=sample_invoice.amount,
                    currency="EUR",
                    source_message_id="msg",
                )
            )
            is False
        )
        assert (
            use_case.validate_invoice_data(
                Invoice(
                    partner_id="partner",
                    invoice_number="INV-2",
                    invoice_date=sample_invoice.invoice_date,
                    amount=Decimal("0"),
                    currency="EUR",
                    source_message_id="msg",
                )
            )
            is False
        )


@pytest.mark.integration
class TestEmailProcessingIntegration:
    """Integration tests for email processing"""

    def test_full_processing_workflow(self):
        """Test full processing workflow"""
        # Integration tests with real components will be added here
        pass
