from datetime import date
from decimal import Decimal

from automation.domain.models import Invoice


def test_invoice_key_is_stable_and_does_not_include_amount():
    invoice = Invoice(
        partner_id="shopify",
        invoice_number="INV-123",
        invoice_date=date(2025, 2, 1),
        amount=Decimal("100.00"),
        currency="EUR",
        source_message_id="<msg-1>",
    )

    assert invoice.invoice_key == "shopify:INV-123:2025-02-01"


def test_invoice_key_same_for_different_amounts():
    inv1 = Invoice(
        partner_id="shopify",
        invoice_number="INV-123",
        invoice_date=date(2025, 2, 1),
        amount=Decimal("100.00"),
        currency="EUR",
        source_message_id="<msg-1>",
    )

    inv2 = Invoice(
        partner_id="shopify",
        invoice_number="INV-123",
        invoice_date=date(2025, 2, 1),
        amount=Decimal("120.00"),
        currency="EUR",
        source_message_id="<msg-2>",
    )

    assert inv1.invoice_key == inv2.invoice_key
