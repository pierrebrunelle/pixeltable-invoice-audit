"""Audit queries."""
import pixeltable as pxt

from models import LineItems


@pxt.query
def flagged(vendor_code: str):
    """Lines for a vendor that are not 'clear', riskiest first."""
    return LineItems.where((LineItems.vendor_code == vendor_code) & (LineItems.band != 'clear')).select(
        LineItems.ref, LineItems.total, LineItems.risk, LineItems.band, LineItems.note_excerpt
    ).order_by(LineItems.risk, asc=False)
