from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from automation.adapters.vub_camt053_parser import VubCamt053Parser


def test_parse_invoice_extracts_core_fields_from_vub_camt053(tmp_path: Path):
    parser = VubCamt053Parser()
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <GrpHdr>
      <MsgId>MSG-2026-0001</MsgId>
      <CreDtTm>2026-03-06T03:15:41.246+01:00</CreDtTm>
    </GrpHdr>
    <Stmt>
      <Id>STATEMENT-2026-03-05</Id>
      <Acct>
        <Ccy>EUR</Ccy>
        <Svcr>
          <FinInstnId>
            <BIC>SUBASKBX</BIC>
            <Nm>Vseobecna uverova banka a.s.</Nm>
          </FinInstnId>
        </Svcr>
      </Acct>
      <TxsSummry>
        <TtlDbtNtries>
          <Sum>28.03</Sum>
        </TtlDbtNtries>
      </TxsSummry>
      <FrToDt>
        <ToDtTm>2026-03-05T00:00:00.000+01:00</ToDtTm>
      </FrToDt>
    </Stmt>
  </BkToCstmrStmt>
</Document>
"""
    file_path = tmp_path / "vub_statement.xml"
    file_path.write_text(xml_content, encoding="utf-8")

    result = parser.parse_invoice(file_path)

    assert result.success is True
    assert result.invoice is not None
    assert result.invoice.invoice_number == "STATEMENT-2026-03-05"
    assert result.invoice.amount == Decimal("28.03")
    assert result.invoice.currency == "EUR"
    assert result.invoice.partner_id == "vseobecna_uverova_banka_a.s."
    assert result.metadata["parser_type"] == "vub_camt053"


def test_can_parse_returns_false_for_non_xml(tmp_path: Path):
    parser = VubCamt053Parser()
    file_path = tmp_path / "note.txt"
    file_path.write_text("camt.053", encoding="utf-8")
    assert parser.can_parse(file_path) is False


def test_parse_invoice_returns_error_for_invalid_xml(tmp_path: Path):
    parser = VubCamt053Parser()
    file_path = tmp_path / "broken.xml"
    file_path.write_text("<Document><Stmt></Document>", encoding="utf-8")

    result = parser.parse_invoice(file_path)

    assert result.success is False
    assert any("XML parsing error" in err for err in result.errors)
