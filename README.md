<!-- pixeltable-example-app: 20260929-invoice-audit -->
# Invoice Audit API built with Pixeltable

[![Built with Pixeltable](https://img.shields.io/badge/built%20with-Pixeltable-5b4bff)](https://pixeltable.com)
[![PyPI - pixeltable](https://img.shields.io/pypi/v/pixeltable?label=pixeltable)](https://pypi.org/project/pixeltable/)
[![GitHub stars](https://img.shields.io/github/stars/pixeltable/pixeltable?style=social)](https://github.com/pixeltable/pixeltable)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Audit vendor invoices line by line. Each line item flows through a **chain of computed columns**: `subtotal → net (after discount) → tax → total`, plus a parallel `risk → band` branch that flags unusual quantities, prices and discounts for the vendor's tier. Every step is a small Python UDF in `udfs.py`, Pixeltable works out the dependency order, and a `/risk` compute route scores a line before it is ever saved.

[Pixeltable](https://pixeltable.com) is open-source, Python-native **multimodal AI data infrastructure**: tables, incremental computed columns, UDFs, indexes and serving in one library, running locally or on Pixeltable Cloud.

> ⭐ **Like this example?** Star [pixeltable/pixeltable](https://github.com/pixeltable/pixeltable) on GitHub. It helps other developers find it.

## What this example shows

- **Incremental computed columns** powered by plain Python UDFs (`@pxt.udf`)
- **`pxt` CLI and local dashboard** for exploring tables and computed columns
- **`pixeltable.toml` project config**: local and Pixeltable Cloud database sizing in one file
- **FastAPI serving**: one `FastAPIRouter` turns tables and `@pxt.query` functions into typed REST routes (insert, update, delete, compute and query) with OpenAPI docs
- **Importable UDF module**: UDFs live in `udfs.py`; tables, queries and routes live together in `app.py` (Pixeltable resolves UDFs by module path)
- **`pixeltable.toml`** declares a local database and a **Pixeltable Cloud** database, so the same code deploys with `pxt db update`

## The computation graph

```
qty, unit_price ─▶ subtotal ─▶ net ─▶ tax ─▶ total
       discount_pct ───────────┘     │
                tax_rate ────────────┘
qty, unit_price, discount_pct, vendor_tier ─▶ risk ─▶ band
vendor_code, sku ─▶ ref        note ─▶ note_excerpt (keyword-only UDF arg n=48)
```

Update a line's `discount_pct` and Pixeltable recomputes `net`, `tax`, `total`, `risk` and `band` in the right order, and leaves `ref` alone. Explore it from the CLI: `pxt computed audit/line_items` lists every computed column with its expression, and `pxt rows audit/line_items -n 5` shows the values.

## What's inside

| File | What it is |
|------|------------|
| `app.py` | The app: tables declared as Python classes, `@pxt.query` functions, and the `FastAPIRouter` routes |
| `client_demo.py` | Score a line, record it, adjust its discount and list flagged lines through the API |
| `pixeltable.toml` | Project config: the local database plus a Pixeltable Cloud database (sizing, deploy excludes) |
| `seed.py` | Seed vendors and a few invoice lines |
| `udfs.py` | Pixeltable UDFs (`@pxt.udf`) in their own importable module, imported by `app.py` |
| `requirements.txt` / `pyproject.toml` | Dependencies (`pixeltable[serve]>=0.7.14`) |

**Tables**

| Table | Stored columns | Computed columns |
|-------|---------|------------------|
| `vendors` | `code`, `name`, `tier`, `active` | `id`, `code_upper`, `tier_upper` |
| `line_items` | `vendor_code`, `sku`, `qty`, `unit_price`, `discount_pct`, `tax_rate`, `vendor_tier`, `note`, `auditor` | `id`, `ref`, `subtotal`, `net`, `tax`, `total`, `risk`, `band`, `note_excerpt` |

**API routes** (service `audit`)

| Method | Path | Kind | Backed by | Notes |
|--------|------|------|-----------|-------|
| `POST` | `/lines` | insert | `LineItems` |  |
| `POST` | `/lines/adjust` | update | `LineItems` |  |
| `POST` | `/vendors` | insert | `Vendors` |  |
| `POST` | `/risk` | compute | `LineItems` |  |
| `GET` | `/flagged` | query | `flagged` |  |

## Quickstart

Requires Python 3.11+ and `pixeltable[serve]>=0.7.14`.

```bash
git clone https://github.com/pierrebrunelle/pixeltable-invoice-audit.git
cd pixeltable-invoice-audit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create the tables in a local catalog directory named `audit`
pxt schema update app.py audit

python seed.py audit
pxt service run app.py audit --port 8000   # open http://localhost:8000/docs
python client_demo.py                     # in another terminal
pxt computed audit/line_items             # every computed column and its expression
```

Try it:

```bash
curl -s -X POST localhost:8000/risk -H 'Content-Type: application/json' -d '{"qty": 500, "unit_price": 12.0, "discount_pct": 35.0, "vendor_tier": "silver"}'
curl -s 'localhost:8000/flagged?vendor_code=nwp'
```

## Deploy to Pixeltable Cloud

The same `app.py` runs on [Pixeltable Cloud](https://pixeltable.com). Sign in (or get a free trial database with `pxt new`), point the second database entry in `pixeltable.toml` at your own database, then deploy:

```bash
pxt login                       # or: export PIXELTABLE_API_KEY=<your-api-key>
# edit pixeltable.toml: name = 'pxt://<your-org>:<your-db>'
pxt db update pxt://<your-org>:<your-db>                 # build the image and upload the project
pxt schema update app.py pxt://<your-org>:<your-db>/audit   # create the tables in the hosted database
pxt service update app.py pxt://<your-org>:<your-db>/audit  # start the API there
pxt service list pxt://<your-org>:<your-db>              # list hosted services
```

Hosted routes require an API key: send it in the `X-api-key` header (for example `-H "X-api-key: $PIXELTABLE_API_KEY"`). Keep keys in environment variables or `pxt secret set`, never in code.

## Code walkthrough

**1. Business logic is plain Python, in `udfs.py`.** A `@pxt.udf` function can be used as a column expression. Pixeltable records UDFs by module path (`udfs.line_subtotal`), so they live in their own importable module rather than inline in the app: the daemon, serving workers and Pixeltable Cloud import it again by that path.

```python
# udfs.py
@pxt.udf
def line_subtotal(qty: int, unit_price: float) -> float:
    return round(qty * unit_price, 2)
```

**2. Tables are Python classes (`app.py`).** Annotated attributes are stored columns; attributes assigned an expression are **computed columns** (`id`, `ref`, `subtotal`, `net`, `tax`, `total`, `risk`, `band`, `note_excerpt`), evaluated incrementally on every insert or update and recomputed when their inputs change.

```python
# app.py
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
```

**3. Queries are functions (`app.py`).** `@pxt.query` wraps a Pixeltable query so it can be called from Python or exposed as a route:

```python
# app.py
@pxt.query
def flagged(vendor_code: str):
    """Lines for a vendor that are not 'clear', riskiest first."""
    return LineItems.where((LineItems.vendor_code == vendor_code) & (LineItems.band != 'clear')).select(
        LineItems.ref, LineItems.total, LineItems.risk, LineItems.band, LineItems.note_excerpt
    ).order_by(LineItems.risk, asc=False)
```

**4. One router, a full REST API.** `FastAPIRouter` generates request/response models from the column types, validates input, and publishes OpenAPI docs at `/docs`:

```python
# app.py
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
```

## Learn more

- 🌐 Website: https://pixeltable.com
- 📚 Docs: https://docs.pixeltable.com
- 💻 Source: https://github.com/pixeltable/pixeltable (⭐ star it if Pixeltable is useful to you)
- 📦 PyPI: https://pypi.org/project/pixeltable/

---

<sub>Built as part of a daily series of Pixeltable example apps · Pixeltable 0.7.14 · Python, FastAPI, incremental computed columns · Licensed under Apache-2.0.</sub>
