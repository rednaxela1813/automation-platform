"""
Ports for document parsing.
Defines interfaces for extracting data from various file types.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from automation.domain.models import Invoice


class DocumentType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    XLSX = "xlsx"
    DOCX = "docx"
    XML = "xml"


class ParseResult:
    """Document parsing result."""

    def __init__(
        self,
        success: bool,
        invoice: Optional[Invoice] = None,
        errors: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.invoice = invoice
        self.errors = errors or []
        self.metadata = metadata or {}


class DocumentParser(Protocol):
    """Document parsing interface."""

    def can_parse(self, file_path: Path) -> bool:
        """Check whether the parser can handle the file."""
        ...

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from a file."""
        ...

    def extract_text(self, file_path: Path) -> str:
        """Extract text from a document."""
        ...


class PDFParser(Protocol):
    """Specialized parser for PDF files."""

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from a PDF file."""
        ...


class ExcelParser(Protocol):
    """Specialized parser for Excel files."""

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from an Excel file."""
        ...


class XMLParser(Protocol):
    """Specialized parser for XML files."""

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from an XML file."""
        ...
