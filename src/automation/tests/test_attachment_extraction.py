from __future__ import annotations

import os

import pytest

from automation.adapters.email_imap import ImapEmailClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_IMAP_TESTS") != "1",
        reason="Manual attachment diagnostic. Set RUN_IMAP_TESTS=1 to enable.",
    ),
]


def test_recent_messages_expose_attachment_metadata():
    client = ImapEmailClient()
    messages = client.fetch_new_messages(force_reprocess=True)

    assert isinstance(messages, list)
    for message in messages[:3]:
        for attachment in message.attachments:
            assert attachment.filename
            assert attachment.content_type is not None
            assert attachment.size >= 0
