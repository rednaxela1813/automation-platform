"""Parser for Websupport / Active24 Slovak invoice PDF files.

These PDFs render text twice (shadow effect), producing doubled characters
like 'FFaakkttúúrraa'. The parser deduplicates before extracting fields.

Typical filename: 726002125.pdf
Keywords in document: 'Faktúra', 'Daňový doklad', 'Celkom s DPH'
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber

from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult

logger = logging.getLogger(__name__)

# Keywords that identify this invoice type
WEBSUPPORT_MARKERS = [
    "daňový doklad",
    "celkom s dph",
    "faktúra",
]


def deduplicate_text(text: str) -> str:
    """
    Fix doubled characters produced by shadow-text PDFs.

    'FFaakkttúúrraa' -> 'Faktúra'
    '1122,,1188 €€'  -> '12,18 €'

    Strategy: for each character, keep it only if it differs from the
    previous kept character OR if the run length so far is odd.
    Works character-by-character so it handles multi-byte chars too.
    """
    if not text:
        return text

    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        # If next char is the same, skip the duplicate
        if i + 1 < len(text) and text[i + 1] == ch:
            result.append(ch)
            i += 2
        else:
            result.append(ch)
            i += 1
    return "".join(result)


class WebsupportPdfParser:
    """Parser for Websupport / Active24 Slovak invoice PDFs."""

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".pdf":
            return False
        try:
            text = self._extract_raw_text(file_path).lower()
            return any(marker in text for marker in WEBSUPPORT_MARKERS)
        except Exception:
            return False

    def parse_invoice(self, file_path: Path) -> ParseResult:
        try:
            raw = self._extract_raw_text(file_path)
            text = deduplicate_text(raw)

            invoice_number = self._extract_invoice_number(text)
            amount = self._extract_amount(text)
            date = self._extract_date(text)
            currency = self._extract_currency(text)
            partner_id = self._extract_partner_id(text)

            if not invoice_number or amount is None:
                return ParseResult(
                    success=False,
                    errors=[
                        f"Missing fields — invoice_number: {invoice_number}, amount: {amount}"
                    ],
                )

            invoice = Invoice(
                partner_id=partner_id,
                invoice_number=invoice_number,
                invoice_date=date,
                amount=amount,
                currency=currency,
                source_message_id=file_path.name,
            )

            return ParseResult(
                success=True,
                invoice=invoice,
                metadata={"parser": "WebsupportPdfParser"},
            )

        except Exception as e:
            logger.exception("Websupport PDF parsing failed: %s", file_path)
            return ParseResult(success=False, errors=[f"Websupport PDF error: {e}"])

    # ── private ──────────────────────────────────────────────────────────────

    def _extract_raw_text(self, file_path: Path) -> str:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _extract_invoice_number(self, text: str) -> str | None:
        """Extract from 'Daňový doklad č. 726002125'"""
        patterns = [
            r"Daňový\s+doklad\s+č\.\s*(\d+)",
            r"Faktúra\s+č\.\s*(\d+)",
            r"Doklad\s+č\.\s*(\d+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_amount(self, text: str) -> Decimal | None:
        """Extract from 'Celkom s\nDPH\n12,18 €' layout."""
        patterns = [
            # Multiline: "Celkom s\nDPH\n12,18"
            r"DPH\s*\n\s*([\d]+[.,]\d{2})",
            # Same line: "Celkom s DPH 12,18"
            r"Celkom\s+s\s+DPH\D{0,5}([\d]+[.,]\d{2})",
            # Fallback: last occurrence of EUR amount
            r"([\d]+[.,]\d{2})\s*€",
        ]
        for pattern in patterns:
            # For last-occurrence fallback, take the last match
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                raw = matches[-1].group(1).strip().replace(" ", "")
                try:
                    return Decimal(raw.replace(",", "."))
                except InvalidOperation:
                    continue
        return None

    def _extract_date(self, text: str) -> datetime.date:
        """Extract from 'Dátum vystavenia\\n16.03.2026' layout."""
        patterns = [
            # Date on next line after label
            r"Dátum\s+vystavenia[^\d]*(\d{1,2}\.\d{2}\.\d{4})",
            r"Dátum\s+vystavenia.*?\n(\d{1,2}\.\d{2}\.\d{4})",
            # Any date in the document
            r"(\d{1,2}\.\d{2}\.\d{4})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if m:
                try:
                    return datetime.strptime(m.group(1).strip(), "%d.%m.%Y").date()
                except ValueError:
                    continue
        return datetime.now().date()

    def _extract_currency(self, text: str) -> str:
        if "€" in text or "EUR" in text:
            return "EUR"
        if "$" in text or "USD" in text:
            return "USD"
        if "CZK" in text:
            return "CZK"
        return "EUR"

    def _extract_partner_id(self, text: str) -> str:
        """Extract supplier name — look for known hosting providers first."""
        # Known suppliers — check directly in text
        known = [
            ("active_24", r"ACTIVE\s*24"),
            ("websupport", r"Websupport"),
            ("websupport", r"wwebsupport"),
        ]
        for partner_id, pattern in known:
            if re.search(pattern, text, re.IGNORECASE):
                return partner_id

        # Fallback: text after 'Dodávateľ' skipping 'Upraviť'
        m = re.search(
            r"Dodávateľ\s*(?:Upraviť\s*)?\n\s*(?:Odberateľ\s*)?(?:Upraviť\s*)?"
            r"[^\n]*\n\s*([A-Z][^\n]{2,40}(?:s\.r\.o\.|a\.s\.|Ltd))",
            text,
            re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip().lower()
            return re.sub(r"[^\w]", "_", name).strip("_")[:40]

        return "websupport"
    