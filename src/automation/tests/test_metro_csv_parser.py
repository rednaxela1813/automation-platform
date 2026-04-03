from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.metro_csv_parser import MetroCsvParser


def test_can_parse_accepts_hdr_csv(tmp_path: Path):
    parser = MetroCsvParser()
    file_path = tmp_path / "invoice.CSV"
    file_path.write_bytes("HDR;INV-1\n".encode("windows-1250"))

    assert parser.can_parse(file_path) is True
    assert parser.can_parse(tmp_path / "invoice.txt") is False


def test_parse_invoice_extracts_core_fields_from_metro_csv(tmp_path: Path):
    parser = MetroCsvParser()
    hdr = [
        "HDR",
        "INV-2026-1001",
        "16.03.2026",
        "METRO Store",
        "",
        "",
        "",
        "",
        "SKK",
        "",
        "VAT123",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "METRO C&C SR",
        "",
        "",
        "",
        "380",
    ]
    lin1 = ["LIN"] + [""] * 10 + ["10.50"]
    lin2 = ["LIN"] + [""] * 10 + ["5.25"]
    file_path = tmp_path / "INV_23201092_2302009314.CSV"
    content = "\n".join([";".join(hdr), ";".join(lin1), ";".join(lin2)])
    file_path.write_bytes(content.encode("windows-1250"))

    result = parser.parse_invoice(file_path)

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "INV-2026-1001"
    assert result.invoice.amount == Decimal("15.75")
    assert result.invoice.currency == "EUR"
    assert result.invoice.partner_id == "metro_c_c_sr"
    assert result.metadata["line_count"] == 2


def test_parse_invoice_returns_error_without_hdr(tmp_path: Path):
    parser = MetroCsvParser()
    file_path = tmp_path / "bad.CSV"
    file_path.write_bytes("LIN;;;;;;;;;;;10.00\n".encode("windows-1250"))

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert result.errors == ["No HDR row found in METRO CSV"]


def test_parse_invoice_returns_error_when_total_cannot_be_calculated(tmp_path: Path):
    parser = MetroCsvParser()
    hdr = ["HDR", "INV-1", "2026-03-16"] + [""] * 20
    lin = ["LIN"] + [""] * 10 + [""]
    file_path = tmp_path / "bad.CSV"
    file_path.write_bytes("\n".join([";".join(hdr), ";".join(lin)]).encode("windows-1250"))

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert result.errors == ["Could not calculate total from LIN rows"]


def test_parse_invoice_returns_error_on_decode_failure(monkeypatch, tmp_path: Path):
    parser = MetroCsvParser()
    file_path = tmp_path / "broken.CSV"
    file_path.write_bytes(b"broken")

    def raise_error(self):
        raise RuntimeError("decode failed")

    monkeypatch.setattr(Path, "read_bytes", raise_error)

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert "METRO CSV parsing error: decode failed" in result.errors[0]


def test_extract_partner_id_and_date_helpers():
    parser = MetroCsvParser()

    assert parser._extract_partner_id("METRO C&C SR") == "metro_c_c_sr"
    assert parser._extract_partner_id("") == "metro"
    assert parser._parse_date("2026-03-16").isoformat() == "2026-03-16"
