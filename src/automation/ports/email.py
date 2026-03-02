"""
Ports for email processing.
Defines interfaces for working with email messages and attachments.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import Message
from typing import List, Protocol


@dataclass(frozen=True)
class EmailAttachment:
    """Email attachment model."""

    filename: str
    content_type: str
    content: bytes
    size: int


@dataclass(frozen=True)
class EmailMessage:
    """Email message model."""

    message_id: str
    subject: str
    sender: str
    received_date: str
    body: str
    attachments: List[EmailAttachment]


class EmailProcessor(Protocol):
    """Email processing interface."""

    def fetch_new_messages(self) -> List[EmailMessage]:
        """Fetch new messages from a mailbox."""
        ...

    def extract_attachments(self, message: Message) -> List[EmailAttachment]:
        """Extract attachments from a message."""
        ...

    def mark_as_processed(self, message_id: str) -> bool:
        """Mark a message as processed."""
        ...
