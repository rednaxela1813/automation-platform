"""Parser for METRO C&C EDI invoice CSV files.

Format: semicolon-delimited EDI with HDR (header) and LIN (line items) rows.
Encoding: Windows-1250 (Central European).

Example filename: INV_23201092_2302009314.CSV
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult

logger = logging.getLogger(__name__)

# HDR row field positions
HDR_INVOICE_NUMBER = 1
HDR_DATE = 2
HDR_STORE_NAME = 3
HDR_CURRENCY = 8        # legacy SKK field — we default to EUR for modern files
HDR_VAT_BUYER = 10
HDR_COMPANY_BUYER = 18
HDR_DOC_TYPE = 22

# LIN row field positions
LIN_PRICE_INCL_VAT = 11   # price including VAT per unit

ENCODING = "windows-1250"
SEPARATOR = ";"

METRO_MARKERS = [
    "METRO",
    "METRO C&C",
    "HDR",
]


class MetroCsvParser:
    """Parser for METRO C&C EDI invoice CSV files."""

    def can_parse(self, file_path: Path) -> bool:
        """Check whether this file looks like a METRO EDI CSV."""
        if file_path.suffix.upper() != ".CSV":
            return False
        try:
            text = file_path.read_bytes().decode(ENCODING, errors="replace")
            first_line = text.split("\n")[0]
            return first_line.startswith("HDR" + SEPARATOR)
        except Exception:
            return False

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse a METRO EDI CSV invoice."""
        try:
            text = file_path.read_bytes().decode(ENCODING, errors="replace")
            lines = [l.rstrip("\r") for l in text.split("\n") if l.strip()]

            hdr = self._find_hdr(lines)
            if not hdr:
                return ParseResult(success=False, errors=["No HDR row found in METRO CSV"])

            invoice_number = self._get(hdr, HDR_INVOICE_NUMBER)
            date_str = self._get(hdr, HDR_DATE)
            company = self._get(hdr, HDR_COMPANY_BUYER)
            doc_type = self._get(hdr, HDR_DOC_TYPE)

            if not invoice_number:
                return ParseResult(success=False, errors=["Invoice number not found in HDR"])

            # Calculate total from LIN rows
            lin_rows = [l.split(SEPARATOR) for l in lines if l.startswith("LIN" + SEPARATOR)]
            total = self._calculate_total(lin_rows)

            if total is None or total <= 0:
                return ParseResult(success=False, errors=["Could not calculate total from LIN rows"])

            invoice_date = self._parse_date(date_str)
            partner_id = self._extract_partner_id(company)

            invoice = Invoice(
                partner_id=partner_id,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                amount=total,
                currency="EUR",
                source_message_id=file_path.name,
            )

            return ParseResult(
                success=True,
                invoice=invoice,
                metadata={
                    "doc_type": doc_type,
                    "store": self._get(hdr, HDR_STORE_NAME),
                    "line_count": len(lin_rows),
                },
            )

        except Exception as e:
            logger.exception("METRO CSV parsing failed: %s", file_path)
            return ParseResult(success=False, errors=[f"METRO CSV parsing error: {e}"])

    def _find_hdr(self, lines: list[str]) -> list[str] | None:
        for line in lines:
            if line.startswith("HDR" + SEPARATOR):
                return line.split(SEPARATOR)
        return None

    def _get(self, row: list[str], index: int) -> str:
        try:
            return row[index].strip()
        except IndexError:
            return ""

    def _calculate_total(self, lin_rows: list[list[str]]) -> Decimal | None:
        """Sum price_incl_vat across all LIN rows."""
        total = Decimal("0")
        found_any = False
        for row in lin_rows:
            try:
                val = self._get(row, LIN_PRICE_INCL_VAT)
                if val:
                    total += Decimal(val)
                    found_any = True
            except (InvalidOperation, IndexError):
                continue
        return total if found_any else None

    def _parse_date(self, date_str: str) -> datetime.date:
        for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return datetime.now().date()

    def _extract_partner_id(self, company: str) -> str:
        if not company:
            return "metro"
        # Normalize: "METRO C&C SR" -> "metro_cc_sr"
        slug = company.lower()
        for ch in [" ", "&", "-", ".", "/"]:
            slug = slug.replace(ch, "_")
        slug = "".join(c for c in slug if c.isalnum() or c == "_")
        return slug.strip("_") or "metro"