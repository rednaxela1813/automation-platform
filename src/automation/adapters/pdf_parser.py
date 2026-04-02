# automation-platform/src/automation/adapters/pdf_parser.py
"""Base adapter for parsing PDF documents."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

import pdfplumber

from automation.config.parser_rules import get_parser_rule_section
from automation.config.settings import settings
from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult

DEFAULT_PATTERNS = {
    "invoice_number": [
        r"(?:Invoice\s*(?:No\.?|Number|#|№|n°)?|Facture\s*n°|Rechnung(?:snr\.?|snummer)?|Factuur(?:nummer)?|Receipt\s*(?:No\.?)?|Booking\s*ID)\s*[:#]?\s*([A-Z0-9#][A-Z0-9/_\-]+)",
        r"(?:Invoice|Bill|Inv|INV)\s*[#№:/]?\s*([A-Z0-9][A-Z0-9/_\-]+)",
    ],
    "amount": [
        r"(?:TOTAL AMOUNT DUE ON[^$€£₹Rs\d]*|Balance Due[:\s]*|Grand Total[:\s]*|Factuur totaal\s*(?:EUR)?\s*|Total TTC\s*[:\s]*)[$€£₹]?\s*(?:Rs\.?)?\s*([0-9]+[.,][0-9]+(?:[.,][0-9]+)?)",
        r"(?:Total|Amount|Sum|Bedrag|Montant|Totaal|Gesamtbetrag)[^0-9]{0,40}[$€£₹]?\s*(?:Rs\.?)?\s*([0-9]+[.,][0-9]{2})",
        r"[$€£₹]\s*([0-9]+[.,][0-9]{2})",
    ],
    "date": [
        r"(?:Invoice Date|Date|Dated|Rechnungsdatum|Factuurdatum|Factuurdatum)\s*[:#]?\s*([A-Za-z]+\s+\d{1,2}\s*,?\s*\d{4})",
        r"(?:Invoice Date|Date|Dated|Rechnungsdatum|Factuurdatum|Order Date)\s*[:#]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{4})\b",
    ],
    "currency": [
        r"\b(EUR|USD|GBP|INR|CHF|PLN|CZK|HUF|DKK|NOK|SEK)\b",
        r"([€$£₹])\s*[0-9]",
        r"[0-9]\s*([€$£₹])",
    ],
}

DEFAULT_CURRENCY_MAP = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
    "¥": "JPY",
    "₽": "RUB",
    "₹": "INR",
    "Rs": "INR",
}


def normalize_amount(amount_str: str) -> Decimal:
    """
    Normalize amount string to Decimal handling both European and US formats.

    Examples:
        "1.234,56" -> Decimal("1234.56")  (European)
        "1,234.56" -> Decimal("1234.56")  (US)
        "1234.56"  -> Decimal("1234.56")
        "1234,56"  -> Decimal("1234.56")  (European no thousands)
        "1939"     -> Decimal("1939")
    """
    s = amount_str.strip().replace(" ", "")

    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # Both separators present — determine which is decimal
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        if last_comma > last_dot:
            # European: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # US: 1,234.56
            s = s.replace(",", "")
    elif has_comma:
        # Only comma — could be European decimal (49,99) or thousands (1,234)
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            # Looks like decimal separator: 49,99
            s = s.replace(",", ".")
        else:
            # Thousands separator: 1,234
            s = s.replace(",", "")
    # Only dot or no separator — already fine

    return Decimal(s)


class PdfInvoiceParser:
    """Parser for extracting invoice data from PDF files."""

    def __init__(self):
        rules = get_parser_rule_section("pdf")
        self._patterns = self._resolve_patterns(rules.get("patterns"))
        self._partner_patterns = self._resolve_list(
            rules.get("partner_patterns"),
            [r"(?:From|Seller|Vendor)[^\n]*?([A-Za-z]+)"],
        )
        self._currency_map = {
            **DEFAULT_CURRENCY_MAP,
            **self._resolve_dict(rules.get("currency_map")),
        }
        self._default_currency = settings.parser_default_currency
        self._default_partner_id = settings.parser_default_partner_id

    @staticmethod
    def _resolve_list(value: Any, defaults: list[str]) -> list[str]:
        if not isinstance(value, list):
            return defaults
        parsed = [str(item).strip() for item in value if str(item).strip()]
        return parsed if parsed else defaults

    @staticmethod
    def _resolve_dict(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        result: dict[str, str] = {}
        for key, item in value.items():
            key_str = str(key).strip()
            item_str = str(item).strip()
            if key_str and item_str:
                result[key_str] = item_str
        return result

    def _resolve_patterns(self, raw_patterns: Any) -> dict[str, list[str]]:
        patterns: dict[str, list[str]] = {}
        if isinstance(raw_patterns, dict):
            for field, defaults in DEFAULT_PATTERNS.items():
                patterns[field] = self._resolve_list(raw_patterns.get(field), defaults)
            return patterns
        return DEFAULT_PATTERNS

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
                    text_content += page_text + "\n"

        return text_content

    def _extract_invoice_data(self, text: str, source_filename: str) -> Optional[Invoice]:
        """Extract structured invoice data from text."""
        extracted_data = {}

        for field, field_patterns in self._patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted_data[field] = match.group(1).strip()
                    break

        if self._validate_extracted_data(extracted_data):
            try:
                amount = normalize_amount(extracted_data["amount"])

                date_str = extracted_data.get("date", "")
                invoice_date = self._parse_date(date_str) if date_str else datetime.now().date()

                return Invoice(
                    partner_id=self._extract_partner_id(text),
                    invoice_number=extracted_data["invoice_number"],
                    invoice_date=invoice_date,
                    amount=amount,
                    currency=self._normalize_currency(
                        extracted_data.get("currency", self._default_currency)
                    ),
                    source_message_id=source_filename,
                )

            except (ValueError, TypeError, InvalidOperation) as e:
                return None

        return None

    def _validate_extracted_data(self, data: dict) -> bool:
        """Check that extracted data contains minimally required fields."""
        required_fields = ["invoice_number", "amount"]
        return all(field in data and data[field] for field in required_fields)

    def _parse_date(self, date_str: str):
        """Parse date from multiple formats."""
        date_formats = [
            "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%B %d , %Y", "%B %d, %Y", "%b %d, %Y", "%b %d , %Y",
            "%d %B %Y", "%d %b %Y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return datetime.now().date()

    def _extract_partner_id(self, text: str) -> str:
        """Extract partner identifier from text."""
        for pattern in self._partner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return self._default_partner_id

    def _normalize_currency(self, token: str) -> str:
        token = token.strip()
        return self._currency_map.get(token, token.upper())