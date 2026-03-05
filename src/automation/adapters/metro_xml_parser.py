"""Parser for Metro Cash & Carry XML invoices."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from lxml import etree

from automation.domain.models import Invoice
from automation.ports.document_parser import ParseResult


class MetroXmlInvoiceParser:
    """Extract invoice fields from Metro-oriented XML payloads."""

    def can_parse(self, file_path: Path) -> bool:
        """Check whether the parser can process the file."""
        return file_path.suffix.lower() == ".xml"

    def parse_invoice(self, file_path: Path) -> ParseResult:
        """Parse an invoice from an XML file."""
        try:
            tree = etree.parse(str(file_path))
            root = tree.getroot()

            invoice_number = self._first_text(
                tree,
                [
                    "/*[local-name()='Invoice']/*[local-name()='ID']",
                    "//*[local-name()='ExchangedDocument']/*[local-name()='ID']",
                    "//*[local-name()='InvoiceNumber']",
                    "//*[contains(local-name(), 'Invoice') and contains(local-name(), 'Number')]",
                ],
            )
            date_raw = self._first_text(
                tree,
                [
                    "/*[local-name()='Invoice']/*[local-name()='IssueDate']",
                    "/*[local-name()='Invoice']/*[local-name()='IssueDate']/*",
                    "//*[local-name()='IssueDate']/*",
                    "//*[local-name()='IssueDate']",
                    "//*[local-name()='InvoiceDate']",
                ],
            )
            amount_raw, currency = self._extract_total_amount(tree)
            partner_id = self._first_text(
                tree,
                [
                    "//*[local-name()='AccountingSupplierParty']//*[local-name()='EndpointID']",
                    "//*[local-name()='AccountingSupplierParty']//*[local-name()='ID']",
                    "//*[local-name()='SellerSupplierParty']//*[local-name()='ID']",
                    "//*[local-name()='Supplier']//*[local-name()='ID']",
                ],
            )

            metadata = {
                "parser_type": "metro_xml",
                "xml_root": etree.QName(root).localname if root is not None else None,
                "xml_namespace": etree.QName(root).namespace if root is not None else None,
                "extracted_fields": {
                    "invoice_number": invoice_number,
                    "invoice_date_raw": date_raw,
                    "amount_raw": amount_raw,
                    "currency": currency,
                    "partner_id": partner_id,
                },
            }

            if not invoice_number or not amount_raw:
                return ParseResult(
                    success=False,
                    errors=["Required XML fields not found: invoice_number and/or amount"],
                    metadata=metadata,
                )

            invoice_date = self._parse_date(date_raw) if date_raw else datetime.now().date()
            amount = self._parse_amount(amount_raw)
            if amount is None:
                return ParseResult(
                    success=False,
                    errors=[f"Failed to parse invoice amount: {amount_raw}"],
                    metadata=metadata,
                )

            invoice = Invoice(
                partner_id=(partner_id or "metro_cash_and_carry").strip().lower(),
                invoice_number=invoice_number.strip(),
                invoice_date=invoice_date,
                amount=amount,
                currency=(currency or "EUR").upper(),
                source_message_id=file_path.name,
            )
            return ParseResult(success=True, invoice=invoice, metadata=metadata)
        except etree.XMLSyntaxError as exc:
            return ParseResult(success=False, errors=[f"XML parsing error: {exc}"])
        except Exception as exc:
            return ParseResult(success=False, errors=[f"XML parsing error: {exc}"])

    def extract_text(self, file_path: Path) -> str:
        """Extract text content from XML file."""
        tree = etree.parse(str(file_path))
        values = [item.strip() for item in tree.getroot().itertext() if item.strip()]
        return "\n".join(values)

    def _first_text(self, tree: etree._ElementTree, xpaths: list[str]) -> Optional[str]:
        """Return first non-empty text value from candidate XPath expressions."""
        for xpath in xpaths:
            nodes = tree.xpath(xpath)
            for node in nodes:
                if isinstance(node, etree._Element):
                    value = "".join(node.itertext()).strip()
                else:
                    value = str(node).strip()
                if value:
                    return value
        return None

    def _extract_total_amount(
        self, tree: etree._ElementTree
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract amount with a preference for invoice total fields."""
        amount_paths = [
            "//*[local-name()='LegalMonetaryTotal']/*[local-name()='PayableAmount']",
            "//*[local-name()='SpecifiedTradeSettlementHeaderMonetarySummation']"
            "/*[local-name()='GrandTotalAmount']",
            "//*[local-name()='PayableAmount']",
            "//*[local-name()='GrandTotalAmount']",
        ]

        for xpath in amount_paths:
            for node in tree.xpath(xpath):
                if not isinstance(node, etree._Element):
                    continue

                value = "".join(node.itertext()).strip()
                if not value:
                    continue

                currency = (
                    node.get("currencyID")
                    or node.get("currency")
                    or self._first_text(
                        tree,
                        [
                            "//*[local-name()='DocumentCurrencyCode']",
                            "//*[local-name()='InvoiceCurrencyCode']",
                        ],
                    )
                )
                return value, currency

        return None, self._first_text(
            tree,
            ["//*[local-name()='DocumentCurrencyCode']", "//*[local-name()='InvoiceCurrencyCode']"],
        )

    def _parse_amount(self, raw_amount: str) -> Optional[Decimal]:
        """Parse amount supporting both comma and dot decimal separators."""
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

        if amount <= 0:
            return None
        return amount

    def _parse_date(self, raw_date: str):
        """Parse common XML invoice date formats."""
        normalized = raw_date.strip()
        if len(normalized) == 8 and normalized.isdigit():
            return datetime.strptime(normalized, "%Y%m%d").date()

        formats = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d")
        for fmt in formats:
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                continue

        return datetime.now().date()
