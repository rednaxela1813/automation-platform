"""Centralized document parser registry."""

from __future__ import annotations

from automation.adapters.excel_parser import ExcelInvoiceParser
from automation.adapters.metro_xml_parser import MetroXmlInvoiceParser
from automation.adapters.pdf_parser import PdfInvoiceParser
from automation.adapters.shopify_pdf_parser import ShopifyPdfInvoiceParser
from automation.adapters.vub_camt053_parser import VubCamt053Parser
from automation.ports.document_parser import DocumentParser
from automation.adapters.metro_csv_parser import MetroCsvParser
from automation.adapters.websupport_pdf_parser import WebsupportPdfParser


def get_document_parsers() -> list[DocumentParser]:
    """Return document parsers in priority order."""
    return [
        ShopifyPdfInvoiceParser(),
        WebsupportPdfParser(), 
        PdfInvoiceParser(),
        VubCamt053Parser(),
        MetroCsvParser(),
       
        ExcelInvoiceParser(),
        MetroXmlInvoiceParser(),
    ]
    
    


