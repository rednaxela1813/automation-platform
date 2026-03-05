"""Local adapter for secure file storage and quarantine."""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from automation.config.settings import settings
from automation.ports.email import EmailAttachment
from automation.ports.file_storage import FileStorageResult
from automation.adapters.security_scanner import SecurityScanner


class LocalFileStorage:
    """Store attachments in safe storage or quarantine based on validation rules."""

    def __init__(self):
        self.safe_storage_dir = Path(settings.safe_storage_dir)
        self.quarantine_dir = Path(settings.quarantine_dir)

        # Ensure storage directories exist.
        self.safe_storage_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # Normalize extension allowlist to lowercase.
        self.allowed_extensions = {ext.lower() for ext in settings.allowed_file_extensions}

        # Convert file size from MB to bytes.
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024

        # Initialize security scanner
        self.security_scanner = SecurityScanner()

    def store_attachment(self, attachment: EmailAttachment) -> tuple[FileStorageResult, str]:
        """Store an attachment and return the storage result plus file path."""
        if not self.is_file_safe(attachment):
            quarantine_path = self._save_to_quarantine(attachment)
            return FileStorageResult.QUARANTINE, str(quarantine_path)

        safe_path = self._save_to_safe_storage(attachment)
        return FileStorageResult.SAFE_STORAGE, str(safe_path)

    def is_file_safe(self, attachment: EmailAttachment) -> bool:
        """Validate attachment safety before storing in safe storage."""
        if not self._has_allowed_extension(attachment.filename):
            return False

        if attachment.size > self.max_file_size:
            return False

        if not self._has_valid_mime_type(attachment):
            return False

        if self._contains_suspicious_content(attachment):
            return False

        # Enhanced security scan
        is_safe, reason = self.security_scanner.scan_file_content(
            attachment.content, attachment.filename
        )
        if not is_safe:
            # Log the security reason for monitoring
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Security scan blocked file {attachment.filename}: {reason}")
            return False

        return True

    def get_safe_files(self) -> List[Path]:
        """Return files currently stored in safe storage."""
        return list(self.safe_storage_dir.glob("**/*"))

    def get_quarantine_files(self) -> List[Path]:
        """Return files currently stored in quarantine."""
        return list(self.quarantine_dir.glob("**/*"))

    def delete_quarantine_file(self, filename: str) -> bool:
        """Delete one file from quarantine."""
        file_path = self.quarantine_dir / filename

        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                return True
            return False
        except (OSError, PermissionError):
            return False

    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Return metadata for one file path."""
        if not file_path.exists():
            return None

        stat = file_path.stat()
        return {
            "name": file_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "extension": file_path.suffix.lower(),
            "hash": self._calculate_file_hash(file_path),
        }

    def _save_to_safe_storage(self, attachment: EmailAttachment) -> Path:
        """Write attachment to safe storage and persist metadata."""
        safe_filename = self._generate_safe_filename(attachment)
        file_path = self.safe_storage_dir / safe_filename

        with open(file_path, "wb") as f:
            f.write(attachment.content)

        self._save_metadata(file_path, attachment)
        return file_path

    def _save_to_quarantine(self, attachment: EmailAttachment) -> Path:
        """Write attachment to quarantine and persist quarantine info."""
        quarantine_filename = f"quarantine_{self._generate_safe_filename(attachment)}"
        file_path = self.quarantine_dir / quarantine_filename

        with open(file_path, "wb") as f:
            f.write(attachment.content)

        self._save_quarantine_info(file_path, attachment)
        return file_path

    def _generate_safe_filename(self, attachment: EmailAttachment) -> str:
        """Generate deterministic safe filename with timestamp and content hash."""
        content_hash = hashlib.md5(attachment.content).hexdigest()[:8]
        safe_name = self._sanitize_filename(attachment.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        name_part = Path(safe_name).stem
        extension = Path(safe_name).suffix
        return f"{timestamp}_{content_hash}_{name_part}{extension}"

    def _sanitize_filename(self, filename: str) -> str:
        """Keep only safe filename characters and clamp length."""
        import re

        safe_chars = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        if len(safe_chars) > 100:
            name_part = safe_chars[:90]
            extension = Path(filename).suffix[:10]
            safe_chars = name_part + extension
        return safe_chars

    def _has_allowed_extension(self, filename: str) -> bool:
        """Check extension against allowlist."""
        extension = Path(filename).suffix.lower()
        return extension in self.allowed_extensions

    def _has_valid_mime_type(self, attachment: EmailAttachment) -> bool:
        """Validate MIME type, with extension fallback for generic binary type."""
        allowed_mime_types = {mime.lower() for mime in settings.allowed_mime_types}
        content_type = (attachment.content_type or "").split(";", 1)[0].strip().lower()

        if content_type in allowed_mime_types:
            return True

        if content_type in {"application/octet-stream", "binary/octet-stream"}:
            return self._has_allowed_extension(attachment.filename)

        guessed_mime, _ = mimetypes.guess_type(attachment.filename)
        if guessed_mime and guessed_mime.lower() in allowed_mime_types:
            return True

        return False

    def _contains_suspicious_content(self, attachment: EmailAttachment) -> bool:
        """Run lightweight suspicious-content checks on the first bytes."""
        content_start = attachment.content[:1024].decode("utf-8", errors="ignore")

        suspicious_patterns = [
            "javascript:",
            "<script",
            "eval(",
            "document.write",
            "shell_exec",
            "system(",
        ]

        content_lower = content_start.lower()
        return any(pattern in content_lower for pattern in suspicious_patterns)

    def _get_rejection_reason(self, attachment: EmailAttachment) -> str:
        """Build a human-readable reason string for quarantine decisions."""
        reasons: list[str] = []

        if not self._has_allowed_extension(attachment.filename):
            reasons.append(f"Blocked extension: {Path(attachment.filename).suffix}")

        if attachment.size > self.max_file_size:
            size_mb = attachment.size / (1024 * 1024)
            reasons.append(f"File too large: {size_mb:.1f}MB")

        if not self._has_valid_mime_type(attachment):
            reasons.append(f"Invalid MIME type: {attachment.content_type}")

        if self._contains_suspicious_content(attachment):
            reasons.append("Suspicious content detected")

        return "; ".join(reasons) if reasons else "Validation failed"

    def _save_metadata(self, file_path: Path, attachment: EmailAttachment) -> None:
        """Save metadata for files in safe storage."""
        metadata = {
            "original_filename": attachment.filename,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "stored_at": datetime.now().isoformat(),
            "file_hash": hashlib.sha256(attachment.content).hexdigest(),
        }

        metadata_path = file_path.with_suffix(".metadata.json")
        import json

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _save_quarantine_info(self, file_path: Path, attachment: EmailAttachment) -> None:
        """Save quarantine metadata for files not accepted into safe storage."""
        quarantine_info = {
            "original_filename": attachment.filename,
            "content_type": attachment.content_type,
            "size": attachment.size,
            "quarantined_at": datetime.now().isoformat(),
            "quarantine_reason": self._get_rejection_reason(attachment),
            "file_hash": hashlib.sha256(attachment.content).hexdigest(),
        }

        info_path = file_path.with_suffix(".quarantine_info.json")
        import json

        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(quarantine_info, f, indent=2, ensure_ascii=False)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash for a file."""
        hash_sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()
