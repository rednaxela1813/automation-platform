from __future__ import annotations

import email
import imaplib
from datetime import datetime
from email.message import Message
from typing import List

from automation.config.settings import settings
from automation.ports.email import EmailAttachment, EmailMessage


class ImapEmailClient:
    def __init__(self) -> None:
        self.host = settings.imap_host
        self.username = settings.imap_user
        self.password = settings.imap_password
        self.mailbox = settings.imap_mailbox

    def fetch_new_messages(self) -> List[EmailMessage]:
        """Fetch unseen IMAP messages and convert them to EmailMessage objects."""
        with imaplib.IMAP4_SSL(self.host) as imap:
            imap.login(self.username, self.password)
            imap.select(self.mailbox)

            status, data = imap.search(None, "UNSEEN")
            if status != "OK":
                return []

            messages = []
            for msg_id in data[0].split():
                status, msg_data = imap.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw = msg_data[0][1]
                if not isinstance(raw, (bytes, bytearray)):
                    continue
                msg = email.message_from_bytes(raw)

                email_message = self._convert_to_email_message(msg, msg_id.decode())
                messages.append(email_message)

            return messages

    def mark_as_processed(self, message_id: str) -> bool:
        """Mark message as read (\Seen)."""
        try:
            with imaplib.IMAP4_SSL(self.host) as imap:
                imap.login(self.username, self.password)
                imap.select(self.mailbox)
                status, _ = imap.store(message_id, "+FLAGS", "\\Seen")
                return status == "OK"
        except Exception:
            return False

    # Backward-compatible alias (can be removed after full codebase update)
    def fetch_unseen_messages(self) -> List[EmailMessage]:
        return self.fetch_new_messages()

    def _convert_to_email_message(self, msg: Message, msg_id: str) -> EmailMessage:
        """Convert email.message.Message to EmailMessage domain object."""
        subject = msg.get("Subject", "No Subject")
        sender = msg.get("From", "Unknown Sender")
        date = msg.get("Date", str(datetime.now()))

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, (bytes, bytearray)):
                        body = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, (bytes, bytearray)):
                body = payload.decode("utf-8", errors="ignore")

        attachments = self._extract_attachments(msg)

        return EmailMessage(
            message_id=msg_id,
            subject=subject,
            sender=sender,
            received_date=date,
            body=body,
            attachments=attachments,
        )

    def _extract_attachments(self, msg: Message) -> List[EmailAttachment]:
        """Extract attachments from multipart email message."""
        attachments: List[EmailAttachment] = []

        if not msg.is_multipart():
            return attachments

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()
            if filename:
                content = part.get_payload(decode=True)
                if isinstance(content, (bytes, bytearray)):
                    attachment = EmailAttachment(
                        filename=filename,
                        content_type=part.get_content_type(),
                        content=bytes(content),
                        size=len(content),
                    )
                    attachments.append(attachment)

        return attachments
