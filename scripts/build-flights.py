"""Build src/assets/flights.json and src/assets/coverage.json from the official records in data/official/.

Sources (both official, both kept verbatim in data/official/):
  data/official/timetable/rows.jsonl      official timetable crawl (scripts/crawl-official-timetable.py)
  data/official/official-2025-raw.json    official 2025 PLUS reference table (historical)

The PLUS tier is derived from the departure time only, following the official rules
(2666: departures 19:00-09:00 Beijing time; 2666-exclusive: 08:00-09:00 and 19:00-20:00).
Nothing is taken from third-party schedules.

Usage:
  python scripts/build-flights.py            # rewrite the assets
  python scripts/build-flights.py --check    # exit 1 when the assets differ from the data (CI)
  python scripts/build-flights.py --force    # accept a large drop in row count
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'src/assets'
DATA = ROOT / 'data/official'
CARRIERS = {'HU': '海南航空', 'CN': '大新华航空', 'JD': '首都航空', 'GS': '天津航空', '8L': '祥鹏航空', 'PN': '西部航空', 'GX': '北部湾航空', 'FU': '福州航空', 'UQ': '乌鲁木齐航空', '9H': '长安航空', 'Y8': '金鹏航空'}
# the 2025 table names some airports instead of cities
TABLE_ALIASES = {'北京首都': 'PEK', '北京大兴': 'PKX', '上海虹桥': 'SHA', '上海浦东': 'PVG', '成都天府': 'TFU', '重庆万州': 'WXN', '重庆江北': 'CKG', '大连周水子': 'DLC', '茅台': 'WMT', '那拉提': 'NLT', '香格里拉': 'DIG'}
# airports the timetable names that the map table does not have yet (name, city, province, lat, lon)
EXTRA_AIRPORTS = {'RUG': ('瑞金机场', '瑞金', '江西', 25.8794, 116.0386)}
# airport-name keywords that pick one airport in a multi-airport city
AIRPORT_KEYWORDS = {'首都': 'PEK', '大兴': 'PKX', '虹桥': 'SHA', '浦东': 'PVG', '双流': 'CTU', '天府': 'TFU', '新舟': 'ZYI', '茅台': 'WMT', '瑞金': 'RUG', '黄金': 'KOW'}


def minutes(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def exclusive(dep):
    m = minutes(dep)
    return 480 < m <= 540 or 1140 <= m < 1200


def load_airports():
    airports = json.loads((ASSETS / 'airports.json').read_text())
    for code, (name, city, province, lat, lon) in EXTRA_AIRPORTS.items():
        airports.setdefault(code, dict(iata=code, city=city, province=province, name=name, lat=lat, lon=lon))
    return airports


def airport_resolver(airports, cities):
    """Map (city code from the query, airport name from the result) to an entry of airports.json."""
    by_city_code = {}
    for c in cities:
        by_city_code.setdefault(c['iata'], c)
    strip = lambda s: re.sub(r'国际|机场|民航', '', s)
    cache = {}

    def resolve(city_code, airport_name):
        key = (city_code, airport_name)
        if key in cache:
            return cache[key]
        for kw, code in AIRPORT_KEYWORDS.items():
            if kw in airport_name and code in airports:
                cache[key] = airports[code]
                return airports[code]
        exact = next((a for a in airports.values() if a['name'] == airport_name), None)
        if exact:
            cache[key] = exact
            return exact
        city_name = by_city_code.get(city_code, {}).get('name', '')
        same_city = [a for a in airports.values() if a['city'] == city_name or a['iata'] == city_code]
        if len(same_city) == 1:
            cache[key] = same_city[0]
            return same_city[0]
        loose = [a for a in airports.values() if strip(a['name']) == strip(airport_name) or strip(airport_name) in a['name'] or strip(a['name']) in airport_name]
        if len(loose) == 1:
            cache[key] = loose[0]
            return loose[0]
        if city_code in airports:
            cache[key] = airports[city_code]
            return airports[city_code]
        sys.exit(f'cannot place airport "{airport_name}" (query city {city_code}); add it to EXTRA_AIRPORTS or AIRPORT_KEYWORDS')

    return resolve


def record(no, origin, dest, dep, arr, days, source):
    return dict(flight_no=no, carrier_name=CARRIERS.get(no[:2], no[:2]), origin_city=origin['city'], dest_city=dest['city'], origin_iata_code=origin['iata'], dest_iata_code=dest['iata'],
                origin_province=origin['province'], dest_province=dest['province'], origin_airport=origin['name'], dest_airport=dest['name'], dep_time=dep, arr_time=arr, days=days,
                is_2666_exclusive=exclusive(dep), source_id=source)


def timetable_rows(airports, cities):
    path = DATA / 'timetable/rows.jsonl'
    latest = {}
    for line in path.read_text().splitlines():
        if line.strip():
            rec = json.loads(line)
            latest[(rec['origin'], rec['dest'])] = rec  # the newest answer per pair wins
    resolve = airport_resolver(airports, cities)
    rows, seen = [], set()
    for rec in latest.values():
        for x in rec['rows']:
            o_name, d_name = [s.strip() for s in x['airport_pair'].split(' - ', 1)]
            o, d = resolve(rec['origin'], o_name), resolve(rec['dest'], d_name)
            dep, arr = x['dep_time'].replace(':', ''), x['arr_time'].replace(':', '')
            dates = re.findall(r'\d{4}\.\d{2}\.\d{2}', x['validity'] or '')  # "YYYY.MM.DD-YYYY.MM.DD"
            start, end = [d.replace('.', '-') for d in dates[:2]] if len(dates) == 2 else (None, None)
            key = (x['flight_no'], o['iata'], d['iata'], dep, arr, x['days'], start, end)
            if key in seen:
                continue
            seen.add(key)
            f = record(x['flight_no'], o, d, dep, arr, x['days'], 'official-timetable')
            f.update(valid_from=start, valid_to=end, fetched_at=rec['fetched_at'][:10], query_pair=f"{rec['origin_name']}→{rec['dest_name']}", official_airport_pair=x['airport_pair'],
                     note=f"官网航班时刻表原文：{x['airport_pair']} {x['flight_no']} {x['dep_time']}-{x['arr_time']} 班期{x['days']} 生效{x['validity']}；查询条件 {rec['origin_name']}→{rec['dest_name']}，抓取于 {rec['fetched_at'][:10]}。")
            rows.append(f)
    rows.sort(key=lambda f: (f['origin_city'], f['dest_city'], f['dep_time'], f['flight_no'], f['valid_from'] or ''))
    for n, f in enumerate(rows, 1):
        f['id'] = f'tt-{n}'
    return rows, latest


def archive_rows(airports):
    aliases = dict(TABLE_ALIASES)
    for code, a in airports.items():
        aliases.setdefault(a['city'], code)
    rows = []
    for n, (no, orig, dest, dep, days, product) in enumerate(json.loads((DATA / 'official-2025-raw.json').read_text()), 2):
        f = record(no, airports[aliases[orig]], airports[aliases[dest]], dep.replace(':', '').zfill(4), '', days, 'official-2025')
        f.update(id=f'archive-{n}', source_row=n, official_product=product, note='官方历史表：更新于2025-10-29；表页适用日期“即日起—12月25日”。未公布到达时刻及逐班生效起止日。')
        rows.append(f)
    return rows


def main(argv):
    check, force = '--check' in argv, '--force' in argv
    airports = load_airports()
    cities = json.loads((DATA / 'timetable/cities.json').read_text())
    tt, queried = timetable_rows(airports, cities)
    archive = archive_rows(airports)
    valid = [f for f in tt if f['valid_from'] and f['valid_to']]
    coverage = {
        'fetched_from': min(r['fetched_at'][:10] for r in queried.values()), 'fetched_to': max(r['fetched_at'][:10] for r in queried.values()),
        'pairs_queried': len(queried), 'pairs_with_schedule': sum(1 for r in queried.values() if r['status'] == 'ok'),
        'timetable_rows': len(tt), 'timetable_flights': len({f['flight_no'] for f in tt}), 'timetable_routes': len({(f['origin_iata_code'], f['dest_iata_code']) for f in tt}),
        'timetable_carriers': len({f['carrier_name'] for f in tt}), 'valid_from': min(f['valid_from'] for f in valid), 'valid_to': max(f['valid_to'] for f in valid),
        'archive_rows': len(archive), 'archive_routes': len({(f['origin_iata_code'], f['dest_iata_code']) for f in archive}), 'archive_carriers': len({f['carrier_name'] for f in archive}),
    }
    flights_text = json.dumps(tt + archive, ensure_ascii=False, separators=(',', ':'))
    coverage_text = json.dumps(coverage, ensure_ascii=False, indent=1)
    airports_text = json.dumps(airports, ensure_ascii=False, separators=(',', ':'))
    outputs = {ASSETS / 'flights.json': flights_text, ASSETS / 'coverage.json': coverage_text, ASSETS / 'airports.json': airports_text}
    previous = (ASSETS / 'coverage.json')
    if previous.exists() and not force:
        before = json.loads(previous.read_text()).get('timetable_rows', 0)
        if before and len(tt) < before * 0.7:
            sys.exit(f'timetable rows dropped from {before} to {len(tt)}; refusing to overwrite (use --force if the drop is real)')
    if check:
        stale = [str(p.relative_to(ROOT)) for p, text in outputs.items() if not p.exists() or p.read_text() != text]
        if stale:
            sys.exit('assets are out of date, run python scripts/build-flights.py: ' + ', '.join(stale))
        print('assets match the official data')
        return
    for p, text in outputs.items():
        p.write_text(text)
    print(json.dumps(coverage, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1:])
