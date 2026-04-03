from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from automation.adapters.pdf_parser import PdfInvoiceParser, normalize_amount


def test_normalize_amount_handles_european_and_us_formats():
    assert normalize_amount("1.234,56") == Decimal("1234.56")
    assert normalize_amount("1,234.56") == Decimal("1234.56")
    assert normalize_amount("1234,56") == Decimal("1234.56")
    assert normalize_amount("1939") == Decimal("1939")


def test_parse_invoice_extracts_invoice_fields(monkeypatch):
    parser = PdfInvoiceParser()
    sample_text = """
    Invoice Number: INV-2024-001
    Date: 20/02/2024
    Total: EUR 150.00
    From: Acme
    """
    monkeypatch.setattr(parser, "extract_text", lambda _: sample_text)

    result = parser.parse_invoice(Path("invoice.pdf"))

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "INV-2024-001"
    assert result.invoice.amount == Decimal("150.00")
    assert result.invoice.invoice_date == date(2024, 2, 20)
    assert result.invoice.partner_id == "acme"
    assert result.invoice.currency == "EUR"


def test_parse_invoice_returns_failure_when_required_fields_missing(monkeypatch):
    parser = PdfInvoiceParser()
    monkeypatch.setattr(parser, "extract_text", lambda _: "Hello without invoice data")

    result = parser.parse_invoice(Path("invoice.pdf"))

    assert result.success is False
    assert result.errors == ["Failed to extract invoice data from PDF"]


def test_parse_invoice_returns_failure_on_extract_text_error(monkeypatch):
    parser = PdfInvoiceParser()

    def raise_error(_):
        raise RuntimeError("pdf broke")

    monkeypatch.setattr(parser, "extract_text", raise_error)

    result = parser.parse_invoice(Path("broken.pdf"))

    assert result.success is False
    assert result.errors == ["PDF parsing error: pdf broke"]


def test_extract_invoice_data_falls_back_to_default_partner_and_currency():
    parser = PdfInvoiceParser()
    invoice = parser._extract_invoice_data(
        "Invoice # INV-7\nTotal: 49,99",
        "invoice.pdf",
    )

    assert invoice is not None
    assert invoice.partner_id == parser._default_partner_id
    assert invoice.currency == parser._default_currency
    assert invoice.amount == Decimal("49.99")


def test_parse_date_returns_today_for_unknown_format():
    parser = PdfInvoiceParser()

    parsed = parser._parse_date("not a date")

    assert isinstance(parsed, date)


def test_extract_text_reads_all_pdf_pages(monkeypatch):
    parser = PdfInvoiceParser()

    class DummyPage:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self):
            return self._text

    class DummyPdf:
        pages = [DummyPage("Page one"), DummyPage("Page two")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("automation.adapters.pdf_parser.pdfplumber.open", lambda _: DummyPdf())

    text = parser.extract_text(Path("invoice.pdf"))

    assert text == "Page one\nPage two\n"
