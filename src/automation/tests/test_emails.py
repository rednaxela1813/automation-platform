from __future__ import annotations

import email
import os

import imaplib
import pytest

from automation.config.settings import settings


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_IMAP_TESTS") != "1",
        reason="Manual mailbox diagnostic. Set RUN_IMAP_TESTS=1 to enable.",
    ),
]


def test_recent_emails_have_accessible_payloads():
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(settings.imap_user, settings.imap_password)
        imap.select(settings.imap_mailbox)

        status, data = imap.search(None, "ALL")
        assert status == "OK"
        message_ids = data[0].split() if data and data[0] else []

        for msg_id in message_ids[-2:]:
            fetch_status, msg_data = imap.fetch(msg_id, "(BODY.PEEK[])")
            assert fetch_status == "OK"
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            assert msg.get("Subject") is not None
