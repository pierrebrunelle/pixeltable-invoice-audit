"""Invoice Audit API built with Pixeltable.

    pxt schema update app.py audit
    pxt service run app.py audit
"""
import pixeltable as pxt
import pixeltable.functions as pxtf
from pixeltable.serving import FastAPIRouter

from udfs import (
    apply_discount,
    excerpt_note,
    grand_total,
    invoice_ref,
    line_subtotal,
    risk_band,
    risk_score,
    tax_amount,
)

# ---- tables ----
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


# ---- queries ----
@pxt.query
def flagged(vendor_code: str):
    """Lines for a vendor that are not 'clear', riskiest first."""
    return LineItems.where((LineItems.vendor_code == vendor_code) & (LineItems.band != 'clear')).select(
        LineItems.ref, LineItems.total, LineItems.risk, LineItems.band, LineItems.note_excerpt
    ).order_by(LineItems.risk, asc=False)


# ---- routes ----
audit = FastAPIRouter(name='audit')
audit.add_insert_route(
    LineItems, path='/lines',
    inputs=[LineItems.vendor_code, LineItems.sku, LineItems.qty, LineItems.unit_price, LineItems.discount_pct,
            LineItems.tax_rate, LineItems.vendor_tier, LineItems.note, LineItems.auditor],
    outputs=[LineItems.id, LineItems.ref, LineItems.subtotal, LineItems.net, LineItems.tax, LineItems.total,
             LineItems.risk, LineItems.band, LineItems.note_excerpt],
)
audit.add_update_route(LineItems, path='/lines/adjust', inputs=[LineItems.discount_pct, LineItems.auditor],
                       outputs=[LineItems.id, LineItems.net, LineItems.total, LineItems.risk, LineItems.band])
audit.add_insert_route(Vendors, path='/vendors', inputs=[Vendors.code, Vendors.name, Vendors.tier, Vendors.active],
                       outputs=[Vendors.id, Vendors.code_upper, Vendors.tier_upper])
audit.add_compute_route(LineItems, path='/risk',
                        inputs=[LineItems.qty, LineItems.unit_price, LineItems.discount_pct, LineItems.vendor_tier],
                        outputs=[LineItems.risk, LineItems.band])
audit.add_query_route(path='/flagged', query=flagged, method='get')
