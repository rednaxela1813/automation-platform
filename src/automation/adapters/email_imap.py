from __future__ import annotations

import email
import imaplib
from email.message import Message
from typing import List

from automation.config.settings import settings


class ImapEmailClient:
    def __init__(self) -> None:
        self.host = settings.imap_host
        self.username = settings.imap_user
        self.password = settings.imap_password
        self.mailbox = settings.imap_mailbox

    def fetch_unseen_messages(self) -> List[Message]:
        with imaplib.IMAP4_SSL(self.host) as imap:
            imap.login(self.username, self.password)
            imap.select(self.mailbox)

            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []

            messages = []
            for msg_id in data[0].split():
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                messages.append(msg)

            return messages
