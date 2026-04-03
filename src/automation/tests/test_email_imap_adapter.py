from __future__ import annotations

from email.message import EmailMessage as MimeEmailMessage

from automation.adapters.email_imap import ImapEmailClient


def _build_message_bytes(*, subject: str = "Invoice", attachment_name: str = "invoice.pdf") -> bytes:
    msg = MimeEmailMessage()
    msg["Subject"] = subject
    msg["From"] = "sender@example.com"
    msg["Date"] = "Fri, 03 Apr 2026 12:00:00 +0000"
    msg.set_content("Body text")
    msg.add_attachment(
        b"pdf-bytes",
        maintype="application",
        subtype="pdf",
        filename=attachment_name,
    )
    return msg.as_bytes()


def test_fetch_new_messages_uses_body_peek_and_unseen_by_default(monkeypatch):
    calls: list[tuple[str, tuple[object, ...]]] = []

    class DummyImap:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username: str, password: str):
            calls.append(("login", (username, password)))
            return "OK", [b"logged"]

        def select(self, mailbox: str):
            calls.append(("select", (mailbox,)))
            return "OK", [b"1"]

        def search(self, charset, criteria: str):
            calls.append(("search", (charset, criteria)))
            return "OK", [b"42"]

        def fetch(self, msg_id: bytes, query: str):
            calls.append(("fetch", (msg_id, query)))
            return "OK", [(b"42", _build_message_bytes())]

    monkeypatch.setattr("automation.adapters.email_imap.imaplib.IMAP4_SSL", lambda host: DummyImap())

    client = ImapEmailClient()
    messages = client.fetch_new_messages()

    assert len(messages) == 1
    assert messages[0].message_id == "42"
    assert messages[0].attachments[0].filename == "invoice.pdf"
    assert ("search", (None, "UNSEEN")) in calls
    assert ("fetch", (b"42", "(BODY.PEEK[])")) in calls


def test_fetch_new_messages_uses_all_when_force_reprocess(monkeypatch):
    class DummyImap:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username: str, password: str):
            return "OK", [b"logged"]

        def select(self, mailbox: str):
            return "OK", [b"1"]

        def search(self, charset, criteria: str):
            assert charset is None
            assert criteria == "ALL"
            return "OK", [b""]

    monkeypatch.setattr("automation.adapters.email_imap.imaplib.IMAP4_SSL", lambda host: DummyImap())

    client = ImapEmailClient()
    assert client.fetch_new_messages(force_reprocess=True) == []


def test_mark_as_processed_sets_seen_flag(monkeypatch):
    calls: list[tuple[str, str, str]] = []

    class DummyImap:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, username: str, password: str):
            return "OK", [b"logged"]

        def select(self, mailbox: str):
            return "OK", [b"1"]

        def store(self, message_id: str, operation: str, flag: str):
            calls.append((message_id, operation, flag))
            return "OK", [b"updated"]

    monkeypatch.setattr("automation.adapters.email_imap.imaplib.IMAP4_SSL", lambda host: DummyImap())

    client = ImapEmailClient()

    assert client.mark_as_processed("123")
    assert calls == [("123", "+FLAGS", "\\Seen")]
