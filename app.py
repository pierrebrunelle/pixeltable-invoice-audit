"""Invoice Audit API built with Pixeltable.

    pxt schema update app.py audit
    pxt service run app.py audit
"""
from pixeltable.serving import FastAPIRouter

from models import LineItems, TableModel, Vendors  # noqa: F401  (TableModel lets `pxt schema` find the models)
from queries import flagged

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
