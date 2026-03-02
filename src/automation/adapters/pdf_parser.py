"""Base adapter for parsing PDF documents."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pdfplumber

from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult


class PdfInvoiceParser:
    """Parser for extracting invoice data from PDF files."""

    def can_parse(self, file_path: Path) -> bool:
        """Check whether the parser can process the file."""
        return file_path.suffix.lower() == ".pdf"

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from a PDF file."""
        try:
            text = self.extract_text(file_path)
            invoice = self._extract_invoice_data(text, file_path.name)

            if invoice:
                return ParseResult(
                    success=True, invoice=invoice, metadata={"extracted_text_length": len(text)}
                )
            else:
                return ParseResult(
                    success=False, errors=["Failed to extract invoice data from PDF"]
                )

        except Exception as e:
            return ParseResult(success=False, errors=[f"PDF parsing error: {str(e)}"])

    def extract_text(self, file_path: Path) -> str:
        """Extract text from a PDF file."""
        text_content = ""

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\\n"

        return text_content

    def _extract_invoice_data(self, text: str, source_filename: str) -> Optional[Invoice]:
        """Extract structured invoice data from text."""

        # Patterns for invoice data extraction
        patterns = {
            "invoice_number": [
                r"(?:Invoice|Bill|Inv)\s*[#№:]?\s*([A-Z0-9/-]+)",
            ],
            "amount": [
                r"(?:Total|Amount|Sum)[^0-9]*([0-9,]+\\.?[0-9]*)",
            ],
            "date": [
                r"(?:Date|Dated)[^0-9]*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
            ],
            "currency": [
                r"([A-Z]{3})\\s*[0-9,]+",  # EUR 100.00
                r"([€$£¥₽])\\s*[0-9,]+",  # €100.00
            ],
        }

        extracted_data = {}

        # Extract each field
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data[field] = match.group(1).strip()
                    break

        # Validate and build Invoice object
        if self._validate_extracted_data(extracted_data):
            try:
                # Normalize amount and date values
                amount_str = extracted_data["amount"].replace(",", "")
                amount = Decimal(amount_str)

                date_str = extracted_data["date"]
                invoice_date = self._parse_date(date_str)

                return Invoice(
                    partner_id=self._extract_partner_id(text),
                    invoice_number=extracted_data["invoice_number"],
                    invoice_date=invoice_date,
                    amount=amount,
                    currency=extracted_data.get("currency", "EUR"),
                    source_message_id=source_filename,  # Temporary fallback: use file name
                )

            except (ValueError, TypeError):
                # Parsing errors are intentionally swallowed here
                return None

        return None

    def _validate_extracted_data(self, data: dict) -> bool:
        """Check that extracted data contains minimally required fields."""
        required_fields = ["invoice_number", "amount"]
        return all(field in data and data[field] for field in required_fields)

    def _parse_date(self, date_str: str):
        """Parse date from multiple formats."""
        date_formats = ["%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Fallback to current date if parsing fails
        return datetime.now().date()

    def _extract_partner_id(self, text: str) -> str:
        """Extract partner identifier from text."""
        # Simple heuristic that can be improved
        partner_patterns = [
            r"(?:From|Seller|Vendor)[^\\n]*?([A-Za-z]+)",
        ]

        for pattern in partner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return "unknown_partner"
