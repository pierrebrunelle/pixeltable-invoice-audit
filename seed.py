"""Seed vendors and a few invoice lines.

Usage:
    python seed.py            # seeds the local `audit` catalog directory
    python seed.py my_dir     # or another directory you passed to `pxt schema update`
"""
import sys
from pathlib import Path

import pixeltable as pxt

target = sys.argv[1] if len(sys.argv) > 1 else 'audit'
HERE = Path(__file__).resolve().parent

SEED = {
    'vendors': [
        {'code': 'acme', 'name': 'Acme Industrial', 'tier': 'gold', 'active': True},
        {'code': 'nwp', 'name': 'Northwind Paper', 'tier': 'bronze', 'active': True},
    ],
    'line_items': [
        {'vendor_code': 'acme', 'sku': 'bolt-m8', 'qty': 400, 'unit_price': 0.42, 'discount_pct': 5.0, 'tax_rate': 0.0875, 'vendor_tier': 'gold', 'note': None, 'auditor': None},
        {'vendor_code': 'nwp', 'sku': 'a4-ream', 'qty': 1200, 'unit_price': 3.9, 'discount_pct': 32.0, 'tax_rate': 0.0875, 'vendor_tier': 'bronze', 'note': 'Year-end bulk order, price agreed by phone', 'auditor': None},
        {'vendor_code': 'nwp', 'sku': 'toner-k', 'qty': 6, 'unit_price': 89.0, 'discount_pct': 0.0, 'tax_rate': 0.0875, 'vendor_tier': 'bronze', 'note': None, 'auditor': None},
    ],
}

for table_name, rows in SEED.items():
    t = pxt.get_table(f'{target}/{table_name}')
    if t.count() > 0:
        print(f'{target}/{table_name} already has {t.count()} rows; skipping')
        continue
    for row in rows:
        for k, v in row.items():
            if isinstance(v, str) and v.startswith('data/'):
                row[k] = str(HERE / v)   # local sample media file
    t.insert(rows)
    print(f'inserted {len(rows)} rows into {target}/{table_name}')
