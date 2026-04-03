from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.websupport_pdf_parser import (
    WebsupportPdfParser,
    deduplicate_text,
)


def test_deduplicate_text_removes_shadow_duplicates():
    assert deduplicate_text("FFaakkttúúrraa") == "Faktúra"
    assert deduplicate_text("1122,,1188 €€") == "12,18 €"


def test_can_parse_accepts_pdf_with_websupport_markers(monkeypatch):
    parser = WebsupportPdfParser()
    monkeypatch.setattr(
        parser,
        "_extract_raw_text",
        lambda _: "Daňový doklad\nCelkom s DPH\n12,18 €",
    )

    assert parser.can_parse(Path("invoice.pdf")) is True
    assert parser.can_parse(Path("invoice.txt")) is False


def test_parse_invoice_extracts_websupport_invoice(monkeypatch):
    parser = WebsupportPdfParser()
    raw_text = """
    DDaaňňoovvýý  ddookkllaadd  čč..  726002125
    DDááttuumm  vvyyssttaavveenniiaa
    16.03.2026
    Celkom s
    DPH
    12,18 €
    ACTIVE 24
    """
    monkeypatch.setattr(parser, "_extract_raw_text", lambda _: raw_text)

    result = parser.parse_invoice(Path("726002125.pdf"))

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "72602125"
    assert result.invoice.amount == Decimal("12.18")
    assert result.invoice.currency == "EUR"
    assert result.invoice.partner_id == "active_24"


def test_parse_invoice_returns_error_when_required_fields_missing(monkeypatch):
    parser = WebsupportPdfParser()
    monkeypatch.setattr(parser, "_extract_raw_text", lambda _: "Faktúra bez sumy")

    result = parser.parse_invoice(Path("broken.pdf"))

    assert result.success is False
    assert "Missing fields" in result.errors[0]


def test_parse_invoice_returns_failure_on_extract_error(monkeypatch):
    parser = WebsupportPdfParser()

    def raise_error(_):
        raise RuntimeError("pdf broke")

    monkeypatch.setattr(parser, "_extract_raw_text", raise_error)

    result = parser.parse_invoice(Path("broken.pdf"))

    assert result.success is False
    assert "Websupport PDF error: pdf broke" in result.errors[0]


def test_extract_partner_id_falls_back_to_slugified_supplier_name():
    parser = WebsupportPdfParser()
    text = "Dodávateľ\nUpraviť\nOdberateľ\nUpraviť\nExample Company s.r.o."

    partner_id = parser._extract_partner_id(text)

    assert partner_id.startswith("example_company")
