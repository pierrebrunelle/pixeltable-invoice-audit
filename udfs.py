"""Pixeltable UDFs for invoice auditing: a money chain and a risk branch (recorded as `udfs.<name>`)."""
import pixeltable as pxt

TIER_LIMITS = {'gold': 25_000.0, 'silver': 10_000.0, 'bronze': 2_500.0}


@pxt.udf
def line_subtotal(qty: int, unit_price: float) -> float:
    return round(qty * unit_price, 2)


@pxt.udf
def apply_discount(subtotal: float, discount_pct: float) -> float:
    return round(subtotal * (1 - discount_pct / 100), 2)


@pxt.udf
def tax_amount(net: float, tax_rate: float) -> float:
    return round(net * tax_rate, 2)


@pxt.udf
def grand_total(net: float, tax: float) -> float:
    return round(net + tax, 2)


@pxt.udf
def risk_score(qty: int, unit_price: float, discount_pct: float, vendor_tier: str) -> int:
    """0-100: large lines for the tier, deep discounts and odd quantities raise the score."""
    limit = TIER_LIMITS.get(vendor_tier, 1_000.0)
    score = min(50, int(50 * (qty * unit_price) / limit))
    score += 30 if discount_pct >= 30 else (10 if discount_pct >= 15 else 0)
    score += 20 if qty >= 1000 or qty % 100 == 0 else 0
    return min(score, 100)


@pxt.udf
def risk_band(risk: int) -> str:
    return 'review' if risk >= 60 else ('watch' if risk >= 30 else 'clear')


@pxt.udf
def invoice_ref(vendor_code: str, sku: str) -> str:
    return f'{vendor_code.upper()}-{sku.upper()}'


@pxt.udf
def excerpt_note(note: str | None, *, n: int = 48) -> str:
    """Keyword-only parameters work in UDFs too: excerpt_note(note, n=24)."""
    t = (note or '').strip()
    return t if len(t) <= n else t[: n - 1] + '…'
