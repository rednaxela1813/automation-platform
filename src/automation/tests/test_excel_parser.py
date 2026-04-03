from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from automation.adapters.excel_parser import ExcelInvoiceParser
from automation.domain.models import Invoice


def test_can_parse_accepts_excel_extensions():
    parser = ExcelInvoiceParser()

    assert parser.can_parse(Path("invoice.xlsx")) is True
    assert parser.can_parse(Path("invoice.xls")) is True
    assert parser.can_parse(Path("invoice.pdf")) is False


def test_parse_invoice_extracts_invoice_from_first_matching_sheet(monkeypatch):
    parser = ExcelInvoiceParser()
    invoice = Invoice(
        partner_id="acme",
        invoice_number="INV-1",
        invoice_date=date(2024, 2, 20),
        amount=Decimal("150.00"),
        currency="EUR",
        source_message_id="invoice.xlsx",
    )

    class DummyWorkbook:
        sheetnames = ["Sheet1", "Sheet2"]

        def __getitem__(self, name):
            return name

        def close(self):
            return None

    monkeypatch.setattr(
        "automation.adapters.excel_parser.openpyxl.load_workbook",
        lambda *args, **kwargs: DummyWorkbook(),
    )
    monkeypatch.setattr(
        parser,
        "_extract_invoice_from_sheet",
        lambda sheet, filename: None if sheet == "Sheet1" else invoice,
    )

    result = parser.parse_invoice(Path("invoice.xlsx"))

    assert result.success is True
    assert result.invoice == invoice
    assert result.metadata == {"sheets_processed": 2}


def test_parse_invoice_returns_failure_when_no_invoice_found(monkeypatch):
    parser = ExcelInvoiceParser()

    class DummyWorkbook:
        sheetnames = ["Sheet1"]

        def __getitem__(self, name):
            return name

        def close(self):
            return None

    monkeypatch.setattr(
        "automation.adapters.excel_parser.openpyxl.load_workbook",
        lambda *args, **kwargs: DummyWorkbook(),
    )
    monkeypatch.setattr(parser, "_extract_invoice_from_sheet", lambda sheet, filename: None)

    result = parser.parse_invoice(Path("invoice.xlsx"))

    assert result.success is False
    assert result.errors == ["Invoice data not found in any sheet"]


def test_parse_invoice_returns_failure_on_load_error(monkeypatch):
    parser = ExcelInvoiceParser()

    def raise_error(*args, **kwargs):
        raise RuntimeError("broken workbook")

    monkeypatch.setattr("automation.adapters.excel_parser.openpyxl.load_workbook", raise_error)

    result = parser.parse_invoice(Path("broken.xlsx"))

    assert result.success is False
    assert result.errors == ["Excel parsing error: broken workbook"]


def test_extract_text_joins_values_from_all_rows(monkeypatch):
    parser = ExcelInvoiceParser()

    class DummySheet:
        def iter_rows(self, values_only=True):
            return [
                ("Invoice INV-1", None),
                ("Total", 150),
            ]

    class DummyWorkbook:
        sheetnames = ["Sheet1"]

        def __getitem__(self, name):
            return DummySheet()

        def close(self):
            return None

    monkeypatch.setattr(
        "automation.adapters.excel_parser.openpyxl.load_workbook",
        lambda *args, **kwargs: DummyWorkbook(),
    )

    text = parser.extract_text(Path("invoice.xlsx"))

    assert text == "Invoice INV-1\nTotal 150"


class DummyCell:
    def __init__(self, value):
        self.value = value


def test_extract_amount_handles_numeric_and_string_values():
    parser = ExcelInvoiceParser()

    assert parser._extract_amount(DummyCell(150.25)) == Decimal("150.25")
    assert parser._extract_amount(DummyCell("1,234.56")) == Decimal("1234.56")
    assert parser._extract_amount(DummyCell("no amount")) is None


def test_extract_date_and_parse_date_string():
    parser = ExcelInvoiceParser()

    assert parser._extract_date(DummyCell(datetime(2024, 2, 20, 10, 0, 0))) == date(2024, 2, 20)
    assert parser._extract_date(DummyCell("20.02.2024")) == date(2024, 2, 20)
    assert parser._parse_date_string("2024-02-20") == date(2024, 2, 20)
    assert parser._parse_date_string("not a date") is None


def test_extract_partner_and_invoice_number():
    parser = ExcelInvoiceParser()

    assert parser._extract_partner("Supplier: Acme") == "acme"
    assert parser._extract_invoice_number("Invoice # INV-2024-001") == "INV-2024-001"
    assert parser._extract_invoice_number("x") is None


def test_extract_invoice_from_sheet_builds_invoice():
    parser = ExcelInvoiceParser()

    class DummySheet:
        max_row = 2
        max_column = 2

        def cell(self, row, column):
            values = {
                (1, 1): DummyCell("Invoice # INV-ABC"),
                (1, 2): DummyCell("Supplier: Acme"),
                (2, 1): DummyCell(datetime(2024, 2, 20, 0, 0, 0)),
                (2, 2): DummyCell(150.00),
            }
            return values.get((row, column), DummyCell(None))

    invoice = parser._extract_invoice_from_sheet(DummySheet(), "invoice.xlsx")

    assert invoice is not None
    assert invoice.invoice_number == "INV-ABC"
    assert invoice.partner_id == "acme"
    assert invoice.amount == Decimal("150.00")
