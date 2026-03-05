from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.metro_xml_parser import MetroXmlInvoiceParser


def test_parse_invoice_extracts_core_fields_from_metro_xml(tmp_path: Path):
    parser = MetroXmlInvoiceParser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
  <ID>INV-2026-1001</ID>
  <IssueDate>2026-03-02</IssueDate>
  <DocumentCurrencyCode>EUR</DocumentCurrencyCode>
  <AccountingSupplierParty>
    <Party>
      <EndpointID>METRO_SK</EndpointID>
    </Party>
  </AccountingSupplierParty>
  <LegalMonetaryTotal>
    <PayableAmount currencyID="EUR">245.90</PayableAmount>
  </LegalMonetaryTotal>
</Invoice>
"""
    file_path = tmp_path / "metro_invoice.xml"
    file_path.write_text(xml_content, encoding="utf-8")

    result = parser.parse_invoice(file_path)

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "INV-2026-1001"
    assert result.invoice.amount == Decimal("245.90")
    assert result.invoice.currency == "EUR"
    assert result.invoice.partner_id == "metro_sk"
    assert result.metadata["parser_type"] == "metro_xml"


def test_parse_invoice_returns_error_for_invalid_xml(tmp_path: Path):
    parser = MetroXmlInvoiceParser()
    file_path = tmp_path / "broken.xml"
    file_path.write_text("<Invoice><ID>123</Invoice>", encoding="utf-8")

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert any("XML parsing error" in err for err in result.errors)


def test_parse_invoice_returns_error_when_required_fields_missing(tmp_path: Path):
    parser = MetroXmlInvoiceParser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice>
  <IssueDate>2026-03-02</IssueDate>
  <DocumentCurrencyCode>EUR</DocumentCurrencyCode>
</Invoice>
"""
    file_path = tmp_path / "incomplete.xml"
    file_path.write_text(xml_content, encoding="utf-8")

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert any("Required XML fields" in err for err in result.errors)
