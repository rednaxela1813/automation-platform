"""
Ports for file storage operations.
Defines interfaces for secure storage and file quarantine.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Protocol

from automation.ports.email import EmailAttachment


class FileStorageResult(Enum):
    """File storage result."""

    SAFE_STORAGE = "safe_storage"
    QUARANTINE = "quarantine"
    REJECTED = "rejected"


class FileStorageService(Protocol):
    """File storage interface."""

    def store_attachment(self, attachment: EmailAttachment) -> tuple[FileStorageResult, str]:
        """
        Save an attachment to the corresponding storage.

        Returns:
            tuple: (result, file path or rejection reason)
        """
        ...

    def is_file_safe(self, attachment: EmailAttachment) -> bool:
        """Check whether a file is safe."""
        ...

    def get_safe_files(self) -> list[Path]:
        """Get a list of files in safe storage."""
        ...

    def get_quarantine_files(self) -> list[Path]:
        """Get a list of files in quarantine."""
        ...

    def delete_quarantine_file(self, filename: str) -> bool:
        """Delete a file from quarantine."""
        ...
