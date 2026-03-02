from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser


def test_parse_invoice_extracts_invoice_amount_and_line_items(monkeypatch):
    parser = ShopifyPdfInvoiceParser()
    sample_text = """
Invoice # INV-2026-0001
Date Mar 2, 2026
From: Shopify
Basic Plan €10.00
Total due €10.00
"""

    monkeypatch.setattr(parser, "extract_text", lambda _: sample_text)

    result = parser.parse_invoice(Path("Novaglen_495776998.pdf"))

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "INV-2026-0001"
    assert result.invoice.amount == Decimal("10.00")
    assert result.invoice.currency == "EUR"
    assert result.invoice.partner_id == "shopify"

    extracted = result.metadata["extracted_fields"]
    assert "Basic Plan" in extracted["description"]
    assert extracted["line_items"] == ["Basic Plan €10.00"]


def test_parse_invoice_returns_error_when_text_extraction_fails(monkeypatch):
    parser = ShopifyPdfInvoiceParser()

    def raise_error(_: Path) -> str:
        raise RuntimeError("broken pdf")

    monkeypatch.setattr(parser, "extract_text", raise_error)

    result = parser.parse_invoice(Path("broken.pdf"))

    assert result.success is False
    assert any("PDF parsing error" in err for err in result.errors)
