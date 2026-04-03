from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import automation.tasks.retry_processing as tasks


def test_retry_failed_invoices_task_returns_zero_when_nothing_retryable(monkeypatch):
    repository = Mock()
    repository.get_retryable_items.return_value = []

    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: object())
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])

    payload = tasks.retry_failed_invoices_task.run()

    assert payload == {"retried": 0, "success": 0, "failed": 0}


def test_retry_failed_invoices_task_retries_successfully(monkeypatch, tmp_path: Path):
    repository = Mock()
    repository.get_retryable_items.return_value = ["invoice-key"]
    repository.reset_for_retry.return_value = True

    safe_file = tmp_path / "invoice-key.pdf"
    safe_file.write_bytes(b"pdf")

    file_storage = Mock()
    file_storage.get_safe_files.return_value = [safe_file]

    parsing_use_case = Mock()
    parsing_use_case.parse_safe_files.return_value = SimpleNamespace()

    export_use_case = Mock()
    export_use_case.export_parsed_invoices.return_value = SimpleNamespace(
        invoices_uploaded=1,
        errors=[],
    )

    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: file_storage)
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "InvoiceParsingUseCase", lambda parsers, repo: parsing_use_case)
    monkeypatch.setattr(tasks, "InvoiceExportUseCase", lambda repo: export_use_case)

    payload = tasks.retry_failed_invoices_task.run()

    assert payload == {"retried": 1, "success": 1, "failed": 0}
    parsing_use_case.parse_safe_files.assert_called_once_with([safe_file])
    export_use_case.export_parsed_invoices.assert_called_once_with([safe_file])
    repository.mark_failed.assert_not_called()


def test_retry_failed_invoices_task_marks_failed_when_source_file_missing(monkeypatch):
    repository = Mock()
    repository.get_retryable_items.return_value = ["invoice-key"]
    repository.reset_for_retry.return_value = True

    file_storage = Mock()
    file_storage.get_safe_files.return_value = []

    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: file_storage)
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "InvoiceParsingUseCase", lambda parsers, repo: Mock())
    monkeypatch.setattr(tasks, "InvoiceExportUseCase", lambda repo: Mock())

    payload = tasks.retry_failed_invoices_task.run()

    assert payload == {"retried": 1, "success": 0, "failed": 1}
    repository.mark_failed.assert_called_once()
    assert "Source file not found during retry" in repository.mark_failed.call_args[0][1]


def test_retry_failed_invoices_task_marks_failed_when_export_does_not_upload(monkeypatch, tmp_path: Path):
    repository = Mock()
    repository.get_retryable_items.return_value = ["invoice-key"]
    repository.reset_for_retry.return_value = True

    safe_file = tmp_path / "invoice-key.pdf"
    safe_file.write_bytes(b"pdf")

    file_storage = Mock()
    file_storage.get_safe_files.return_value = [safe_file]

    export_use_case = Mock()
    export_use_case.export_parsed_invoices.return_value = SimpleNamespace(
        invoices_uploaded=0,
        errors=["still broken"],
    )

    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: file_storage)
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "InvoiceParsingUseCase", lambda parsers, repo: Mock())
    monkeypatch.setattr(tasks, "InvoiceExportUseCase", lambda repo: export_use_case)

    payload = tasks.retry_failed_invoices_task.run()

    assert payload == {"retried": 1, "success": 0, "failed": 1}
    repository.mark_failed.assert_called_once()
    assert "Retry failed: still broken" in repository.mark_failed.call_args[0][1]


def test_retry_failed_invoices_task_retries_task_on_top_level_exception(monkeypatch):
    class RetryRequested(Exception):
        pass

    monkeypatch.setattr(
        tasks,
        "create_processed_invoice_repository",
        lambda url: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    monkeypatch.setattr(
        tasks.retry_failed_invoices_task,
        "retry",
        lambda exc, countdown: (_ for _ in ()).throw(RetryRequested((str(exc), countdown))),
    )

    try:
        tasks.retry_failed_invoices_task.run()
        assert False, "Expected retry"
    except RetryRequested as exc:
        assert exc.args[0] == ("db down", 60)


def test_cleanup_old_records_task_returns_deleted_count(monkeypatch):
    repository = Mock()
    repository.cleanup_old_records.return_value = 7
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)

    payload = tasks.cleanup_old_records_task.run()

    assert payload == {"deleted_records": 7}
    repository.cleanup_old_records.assert_called_once_with(days_old=90)


def test_get_processing_status_task_returns_summary(monkeypatch):
    repository = Mock()
    repository.get_status_summary.return_value = {"done": 3, "failed_retryable": 1}
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: repository)

    payload = tasks.get_processing_status_task.run()

    assert payload == {"done": 3, "failed_retryable": 1}
