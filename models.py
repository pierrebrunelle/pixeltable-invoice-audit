"""Vendors and invoice line items with a multi-step computed-column chain."""
import pixeltable as pxt
import pixeltable.functions as pxtf

from udfs import (apply_discount, excerpt_note, grand_total, invoice_ref, line_subtotal, risk_band, risk_score,
                  tax_amount)

TableModel = pxt.model_base()


class Vendors(TableModel, name='vendors'):
    id = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    code: pxt.String
    name: pxt.String
    tier: pxt.String
    active: pxt.Bool

    code_upper = pxtf.string.upper(code)
    tier_upper = pxtf.string.upper(tier)


class LineItems(TableModel, name='line_items'):
    id = pxt.Column(value=pxtf.uuid.uuid7(), primary_key=True)
    vendor_code: pxt.String
    sku: pxt.String
    qty: pxt.Int
    unit_price: pxt.Float
    discount_pct: pxt.Float
    tax_rate: pxt.Float
    vendor_tier: pxt.String
    note: pxt.String | None
    auditor: pxt.String | None

    ref = invoice_ref(vendor_code, sku)
    subtotal = line_subtotal(qty, unit_price)
    net = apply_discount(subtotal, discount_pct)
    tax = tax_amount(net, tax_rate)
    total = grand_total(net, tax)
    risk = risk_score(qty, unit_price, discount_pct, vendor_tier)
    band = risk_band(risk)
    note_excerpt = excerpt_note(note, n=48)
