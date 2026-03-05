"""Security scanning utilities for enhanced file validation."""

from __future__ import annotations

import logging
import socket
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import pdfplumber

from automation.config.settings import settings

logger = logging.getLogger(__name__)


class SecurityScanner:
    """Enhanced security scanning for uploaded files."""

    def __init__(self):
        self.enable_clamav = settings.enable_clamav
        self.clamav_socket = settings.clamav_socket

    def scan_file_content(self, content: bytes, filename: str) -> tuple[bool, Optional[str]]:
        """
        Comprehensive file security scan.
        
        Returns:
            (is_safe, reason) - True if safe, False with reason if blocked
        """
        # 1. Check dangerous extensions
        if self._has_dangerous_extension(filename):
            return False, f"Dangerous file extension detected: {Path(filename).suffix}"

        # 2. Check for zip bombs
        if self._is_zip_bomb(content, filename):
            return False, "Potential zip bomb detected"

        # 3. Check PDF page limits  
        if filename.lower().endswith('.pdf'):
            if not self._validate_pdf_limits(content):
                return False, f"PDF exceeds page limit ({settings.max_pdf_pages} pages)"

        # 4. Antivirus scan (if enabled)
        if self.enable_clamav:
            virus_result = self._scan_with_clamav(content)
            if virus_result is not None:
                return False, f"Virus detected: {virus_result}"

        return True, None

    def _has_dangerous_extension(self, filename: str) -> bool:
        """Check if file has dangerous extension."""
        extension = Path(filename).suffix.lower()
        return extension in [ext.lower() for ext in settings.dangerous_extensions]

    def _is_zip_bomb(self, content: bytes, filename: str) -> bool:
        """Detect potential zip bombs by checking compression ratios."""
        if not filename.lower().endswith(('.zip', '.rar', '.7z', '.tar.gz')):
            return False
            
        if not filename.lower().endswith('.zip'):
            # For now only handle ZIP files, extend for others later
            return False

        try:
            with zipfile.ZipFile(BytesIO(content), 'r') as zf:
                # Check number of files
                if len(zf.namelist()) > settings.max_archive_files:
                    logger.warning(f"Archive has too many files: {len(zf.namelist())}")
                    return True

                total_compressed = sum(info.compress_size for info in zf.infolist())
                total_uncompressed = sum(info.file_size for info in zf.infolist())

                if total_compressed == 0:
                    return False  # Empty archive is not a bomb

                ratio = total_uncompressed / total_compressed
                if ratio > settings.max_archive_ratio:
                    logger.warning(f"Suspicious compression ratio: {ratio:.2f}")
                    return True

        except (zipfile.BadZipFile, Exception) as e:
            logger.warning(f"Could not analyze zip file {filename}: {e}")
            # Treat corrupted archives as potentially dangerous
            return True

        return False

    def _validate_pdf_limits(self, content: bytes) -> bool:
        """Check PDF page count limits."""
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                page_count = len(pdf.pages)
                if page_count > settings.max_pdf_pages:
                    logger.warning(f"PDF has too many pages: {page_count}")
                    return False

                # Also check total text size (anti-bomb measure)
                total_text_size = 0
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    total_text_size += len(text.encode('utf-8'))
                    
                    # Early break if too much text
                    if total_text_size > settings.max_text_size_kb * 1024:
                        logger.warning(f"PDF text content too large: {total_text_size} bytes")
                        return False

        except Exception as e:
            logger.warning(f"Could not validate PDF limits: {e}")
            # Treat malformed PDFs as potentially dangerous
            return False

        return True

    def _scan_with_clamav(self, content: bytes) -> Optional[str]:
        """
        Scan content with ClamAV daemon.
        
        Returns:
            None if clean, virus name if infected
        """
        try:
            # Connect to ClamAV daemon
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.clamav_socket)

            # Send INSTREAM command
            sock.sendall(b'zINSTREAM\0')

            # Send file content in chunks
            chunk_size = 4096
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                sock.sendall(len(chunk).to_bytes(4, 'big') + chunk)

            # Signal end of stream
            sock.sendall(b'\x00\x00\x00\x00')

            # Read response
            response = sock.recv(1024).decode('utf-8').strip()
            sock.close()

            if 'FOUND' in response:
                # Extract virus name
                virus_name = response.split(':')[1].strip().replace(' FOUND', '')
                return virus_name
            elif 'OK' in response:
                return None
            else:
                logger.error(f"Unexpected ClamAV response: {response}")
                return "SCAN_ERROR"

        except Exception as e:
            logger.error(f"ClamAV scan failed: {e}")
            # On scan failure, be conservative
            return "SCAN_FAILURE"