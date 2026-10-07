"""Refresh data/airports/ourairports-cn.csv: Chinese airports with an IATA code from
datasets/airport-codes (OurAirports, PDDL). Used only for map coordinates and the province
of airports that the official timetable names but src/assets/airports.json does not know yet.

Usage: python scripts/fetch-airport-codes.py [path-to-local-airport-codes.csv]
"""
import csv
import io
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/airports/ourairports-cn.csv'
URL = 'https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv'
FIELDS = ['iata_code', 'ident', 'type', 'name', 'iso_region', 'municipality', 'coordinates']

source = Path(sys.argv[1]).read_text(encoding='utf-8') if len(sys.argv) > 1 else urllib.request.urlopen(URL, timeout=120).read().decode('utf-8')
rows = [r for r in csv.DictReader(io.StringIO(source)) if r['iso_country'] == 'CN' and r['iata_code'] and r['type'] != 'closed']
rows.sort(key=lambda r: r['iata_code'])
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
print(f'{len(rows)} Chinese airports with IATA codes written to {OUT.relative_to(ROOT)}')
