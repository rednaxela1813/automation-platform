"""Parser for VUB camt.053 bank statement XML files."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from lxml import etree

from automation.config.parser_rules import get_parser_rule_section
from automation.config.settings import settings
from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult

DEFAULT_BANK_MARKERS = [
    "camt.053",
    "vseobecna uverova banka",
    "subaskbx",
]
DEFAULT_INVOICE_NUMBER_XPATHS = [
    "//*[local-name()='Stmt']/*[local-name()='Id']",
    "//*[local-name()='GrpHdr']/*[local-name()='MsgId']",
]
DEFAULT_DATE_XPATHS = [
    "//*[local-name()='Stmt']/*[local-name()='FrToDt']/*[local-name()='ToDtTm']",
    "//*[local-name()='Stmt']/*[local-name()='CreDtTm']",
    "//*[local-name()='GrpHdr']/*[local-name()='CreDtTm']",
]
DEFAULT_AMOUNT_XPATHS = [
    "//*[local-name()='TxsSummry']/*[local-name()='TtlDbtNtries']/*[local-name()='Sum']",
    "//*[local-name()='TxsSummry']/*[local-name()='TtlNtries']/*[local-name()='Sum']",
]
DEFAULT_CURRENCY_XPATHS = [
    "//*[local-name()='Stmt']/*[local-name()='Acct']/*[local-name()='Ccy']",
    "//*[local-name()='Bal']/*[local-name()='Amt']/@Ccy",
    "//*[local-name()='Ntry']/*[local-name()='Amt']/@Ccy",
]
DEFAULT_PARTNER_XPATHS = [
    "//*[local-name()='Stmt']/*[local-name()='Acct']/*[local-name()='Svcr']//*[local-name()='Nm']",
    "//*[local-name()='Stmt']/*[local-name()='Acct']/*[local-name()='Svcr']//*[local-name()='BIC']",
]


class VubCamt053Parser:
    """Extract pseudo-invoice fields from VUB camt.053 statement XML."""

    def __init__(self):
        rules = get_parser_rule_section("vub_camt053")
        self._bank_markers = self._resolve_list(rules.get("bank_markers"), DEFAULT_BANK_MARKERS)
        self._invoice_number_xpaths = self._resolve_list(
            rules.get("invoice_number_xpaths"), DEFAULT_INVOICE_NUMBER_XPATHS
        )
        self._date_xpaths = self._resolve_list(rules.get("date_xpaths"), DEFAULT_DATE_XPATHS)
        self._amount_xpaths = self._resolve_list(rules.get("amount_xpaths"), DEFAULT_AMOUNT_XPATHS)
        self._currency_xpaths = self._resolve_list(
            rules.get("currency_xpaths"), DEFAULT_CURRENCY_XPATHS
        )
        self._partner_xpaths = self._resolve_list(
            rules.get("partner_xpaths"),
            DEFAULT_PARTNER_XPATHS,
        )
        self._default_partner_id = self._resolve_str(
            rules.get("default_partner_id"), "vub_bank_statement"
        )
        self._default_currency = self._resolve_str(
            rules.get("default_currency"), settings.parser_default_currency
        )

    @staticmethod
    def _resolve_list(value: Any, defaults: list[str]) -> list[str]:
        if not isinstance(value, list):
            return defaults
        parsed = [str(item).strip() for item in value if str(item).strip()]
        return parsed if parsed else defaults

    @staticmethod
    def _resolve_str(value: Any, default: str) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return default

    def can_parse(self, file_path: Path) -> bool:
        """Check if file looks like VUB camt.053 statement XML."""
        if file_path.suffix.lower() != ".xml":
            return False
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            return False
        return all(marker in text for marker in self._bank_markers[:1]) and any(
            marker in text for marker in self._bank_markers
        )

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse bank statement fields into Invoice model."""
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            invoice_number = self._first_text(tree, self._invoice_number_xpaths)
            date_raw = self._first_text(tree, self._date_xpaths)
            amount_raw = self._first_text(tree, self._amount_xpaths)
            currency = self._first_text(tree, self._currency_xpaths) or self._default_currency
            partner_raw = self._first_text(tree, self._partner_xpaths)

            metadata = {
                "parser_type": "vub_camt053",
                "xml_root": etree.QName(root).localname if root is not None else None,
                "xml_namespace": etree.QName(root).namespace if root is not None else None,
                "extracted_fields": {
                    "invoice_number": invoice_number,
                    "invoice_date_raw": date_raw,
                    "amount_raw": amount_raw,
                    "currency": currency,
                    "partner_raw": partner_raw,
                },
            }

            if not invoice_number or not amount_raw:
                return ParseResult(
                    success=False,
                    errors=["Required VUB XML fields not found: statement id and/or amount"],
                    metadata=metadata,
                )

            amount = self._parse_amount(amount_raw)
            if amount is None:
                return ParseResult(
                    success=False,
                    errors=[f"Failed to parse statement amount: {amount_raw}"],
                    metadata=metadata,
                )

            invoice_date = self._parse_date(date_raw) if date_raw else datetime.now().date()
            partner_id = self._normalize_partner_id(partner_raw) or self._default_partner_id

            invoice = Invoice(
                partner_id=partner_id,
                invoice_number=invoice_number.strip(),
                invoice_date=invoice_date,
                amount=amount,
                currency=(currency or self._default_currency).upper(),
                source_message_id=file_path.name,
            )
            return ParseResult(success=True, invoice=invoice, metadata=metadata)
        except etree.XMLSyntaxError as exc:
            return ParseResult(success=False, errors=[f"XML parsing error: {exc}"])
        except Exception as exc:
            return ParseResult(success=False, errors=[f"XML parsing error: {exc}"])

    def _first_text(self, tree: etree._ElementTree, xpaths: list[str]) -> Optional[str]:
        for xpath in xpaths:
            for node in tree.xpath(xpath):
                if isinstance(node, etree._Element):
                    value = "".join(node.itertext()).strip()
                else:
                    value = str(node).strip()
                if value:
                    return value
        return None

    def _parse_amount(self, raw_amount: str) -> Optional[Decimal]:
        cleaned = raw_amount.replace(" ", "").replace("\u00a0", "")
        if not cleaned:
            return None
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        try:
            amount = Decimal(cleaned)
        except InvalidOperation:
            return None

        return amount if amount > 0 else None

    def _parse_date(self, raw_date: str):
        normalized = raw_date.strip()
        if not normalized:
            return datetime.now().date()

        if "T" in normalized:
            try:
                return datetime.fromisoformat(normalized).date()
            except ValueError:
                pass

        formats = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d")
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue
        return datetime.now().date()

    def _normalize_partner_id(self, partner_raw: Optional[str]) -> Optional[str]:
        if not partner_raw:
            return None
        cleaned = partner_raw.strip().lower()
        cleaned = "_".join(cleaned.split())
        return cleaned[:64] if cleaned else None
