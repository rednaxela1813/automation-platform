from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser


def test_extract_invoice_number_falls_back_to_filename_digits():
    parser = ShopifyPdfInvoiceParser()

    number = parser._extract_invoice_number("Completely unrelated text", "Shopify_20260316_495776998.pdf", [])

    assert number == "20260316"


def test_extract_date_falls_back_to_filename_date():
    parser = ShopifyPdfInvoiceParser()

    extracted = parser._extract_date("No date here", "Shopify_20260316_invoice.pdf", [])

    assert extracted == "16.03.2026"


def test_parse_amount_helpers_cover_line_and_text_variants():
    parser = ShopifyPdfInvoiceParser()

    amount, currency = parser._parse_amount_from_line("Total due EUR 1,234.56")
    assert amount == Decimal("1234.56")
    assert currency == "EUR"

    amount2, currency2 = parser._parse_amount_from_text("Amount due $10.00")
    assert amount2 == Decimal("10.00")
    assert currency2 == "USD"


def test_extract_partner_uses_from_line_and_filename_fallback():
    parser = ShopifyPdfInvoiceParser()

    assert parser._extract_partner("From: ACME Corp", "invoice.pdf") == "acme_corp"
    assert parser._extract_partner("No partner", "Acme-20260316.pdf") == "acme"


def test_extract_description_and_line_items_filters_totals():
    parser = ShopifyPdfInvoiceParser()
    lines = [
        "Basic Plan €10.00",
        "Subtotal €10.00",
        "VAT €2.00",
        "Basic Plan €10.00",
    ]

    assert parser._extract_description(lines) == "Basic Plan €10.00"
    assert parser._extract_line_items(lines) == ["Basic Plan €10.00"]


def test_parse_date_returns_today_for_invalid_value():
    parser = ShopifyPdfInvoiceParser()

    parsed = parser._parse_date("not a date")

    assert parsed is not None


def test_parse_invoice_failure_includes_extracted_metadata(monkeypatch):
    parser = ShopifyPdfInvoiceParser()
    monkeypatch.setattr(parser, "extract_text", lambda _: "From: Shopify")

    result = parser.parse_invoice(Path("broken.pdf"))

    assert result.success is False
    assert result.metadata["parser_type"] == "shopify_optimized"
    assert "extracted_fields" in result.metadata
