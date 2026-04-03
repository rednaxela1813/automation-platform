from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import automation.tasks.email_processing as tasks


def test_process_new_emails_task_returns_summary(monkeypatch):
    result = SimpleNamespace(
        messages_processed=3,
        files_processed=2,
        invoices_found=1,
        invoices_uploaded=1,
        files_quarantined=4,
        emails_without_attachments=1,
        emails_marked_processed=1,
        parser_failures=2,
        errors=["e1", "e2"],
    )
    use_case = Mock()
    use_case.process_new_emails.return_value = result

    monkeypatch.setattr(tasks, "ImapEmailClient", lambda: object())
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: object())
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: object())
    monkeypatch.setattr(tasks, "EmailProcessingUseCase", lambda **kwargs: use_case)

    payload = tasks.process_new_emails_task.run()

    assert payload == {
        "status": "success",
        "messages_processed": 3,
        "files_processed": 2,
        "invoices_found": 1,
        "invoices_uploaded": 1,
        "files_quarantined": 4,
        "emails_without_attachments": 1,
        "emails_marked_processed": 1,
        "parser_failures": 2,
        "errors": ["e1", "e2"],
    }
    use_case.process_new_emails.assert_called_once_with()


def test_process_new_emails_task_limits_error_list(monkeypatch):
    result = SimpleNamespace(
        messages_processed=0,
        files_processed=0,
        invoices_found=0,
        invoices_uploaded=0,
        files_quarantined=0,
        emails_without_attachments=0,
        emails_marked_processed=0,
        parser_failures=0,
        errors=[f"err-{i}" for i in range(12)],
    )
    use_case = Mock()
    use_case.process_new_emails.return_value = result

    monkeypatch.setattr(tasks, "ImapEmailClient", lambda: object())
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: object())
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: object())
    monkeypatch.setattr(tasks, "EmailProcessingUseCase", lambda **kwargs: use_case)

    payload = tasks.process_new_emails_task.run()

    assert len(payload["errors"]) == 10
    assert payload["errors"][0] == "err-0"
    assert payload["errors"][-1] == "err-9"


def test_process_new_emails_task_retries_on_failure(monkeypatch):
    class RetryRequested(Exception):
        pass

    def raising_use_case(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(tasks, "ImapEmailClient", lambda: object())
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: object())
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: object())
    monkeypatch.setattr(tasks, "EmailProcessingUseCase", raising_use_case)
    monkeypatch.setattr(
        tasks.process_new_emails_task,
        "retry",
        lambda exc: (_ for _ in ()).throw(RetryRequested(str(exc))),
    )

    try:
        tasks.process_new_emails_task.run()
        assert False, "Expected retry"
    except RetryRequested as exc:
        assert "boom" in str(exc)


def test_process_new_emails_task_returns_failed_when_retries_exhausted(monkeypatch):
    monkeypatch.setattr(tasks, "ImapEmailClient", lambda: object())
    monkeypatch.setattr(tasks, "LocalFileStorage", lambda: object())
    monkeypatch.setattr(tasks, "get_document_parsers", lambda: ["parser"])
    monkeypatch.setattr(tasks, "create_processed_invoice_repository", lambda url: object())
    monkeypatch.setattr(tasks, "EmailProcessingUseCase", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    max_retries_exc = tasks.process_new_emails_task.MaxRetriesExceededError
    monkeypatch.setattr(
        tasks.process_new_emails_task,
        "retry",
        lambda exc: (_ for _ in ()).throw(max_retries_exc()),
    )

    payload = tasks.process_new_emails_task.run()

    assert payload == {"status": "failed", "error": "boom", "messages_processed": 0}


def test_process_single_email_task_returns_success():
    payload = tasks.process_single_email_task.run({"message_id": "abc-123"})

    assert payload["status"] == "success"
    assert payload["message_id"] == "abc-123"
    assert "processed_at" in payload


def test_send_processing_report_task_returns_report():
    payload = tasks.send_processing_report_task.run("weekly")

    assert payload["status"] == "success"
    assert payload["report"]["period"] == "weekly"
    assert payload["report"]["emails_processed"] == 42
