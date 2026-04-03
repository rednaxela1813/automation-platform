from __future__ import annotations

import os

import imaplib
import pytest

from automation.config.settings import settings


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_IMAP_TESTS") != "1",
        reason="Manual IMAP diagnostic. Set RUN_IMAP_TESTS=1 to enable.",
    ),
]


def test_imap_connection():
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        result = imap.login(settings.imap_user, settings.imap_password)
        assert result[0] == "OK"

        status, count = imap.select(settings.imap_mailbox)
        assert status == "OK"
        assert count

        status, messages = imap.search(None, "ALL")
        assert status == "OK"
        assert messages is not None
