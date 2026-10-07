"""Build src/assets/flights.json and src/assets/coverage.json from the official records in data/official/.

Sources (both official, both kept verbatim in data/official/):
  data/official/timetable/rows.jsonl      official timetable crawl (scripts/crawl-official-timetable.py)
  data/official/official-2025-raw.json    official 2025 PLUS reference table (historical)
Map positions: data/airports/map-airports.json (curated) plus data/airports/ourairports-cn.csv for
airports the timetable names that the curated table lacks.

The PLUS tier is derived from the departure time only, following the official rules
(2666: departures 19:00-09:00 Beijing time; 2666-exclusive: 08:00-09:00 and 19:00-20:00).
Nothing is taken from third-party schedules.

Usage:
  python scripts/build-flights.py            # rewrite the assets
  python scripts/build-flights.py --check    # exit 1 when the assets differ from the data (CI)
  python scripts/build-flights.py --force    # accept a large drop in row count
"""
import csv
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
EXTRA_AIRPORTS = {'RUG': ('瑞金机场', '瑞金', '江西', 25.8794, 116.0386), 'LTJ': ('巴音郭楞轮台机场', '轮台', '新疆', 41.7833, 84.25), 'XYI': ('三沙永兴机场', '三沙', '海南', 16.8333, 112.3333)}
# ISO 3166-2:CN region codes (as used by OurAirports) to the province names of airports.json
PROVINCES = {'11': '北京', '12': '天津', '13': '河北', '14': '山西', '15': '内蒙古', '21': '辽宁', '22': '吉林', '23': '黑龙江', '31': '上海', '32': '江苏', '33': '浙江', '34': '安徽', '35': '福建', '36': '江西', '37': '山东',
             '41': '河南', '42': '湖北', '43': '湖南', '44': '广东', '45': '广西', '46': '海南', '50': '重庆', '51': '四川', '52': '贵州', '53': '云南', '54': '西藏', '61': '陕西', '62': '甘肃', '63': '青海', '64': '宁夏', '65': '新疆',
             'BJ': '北京', 'TJ': '天津', 'HE': '河北', 'SX': '山西', 'NM': '内蒙古', 'LN': '辽宁', 'JL': '吉林', 'HL': '黑龙江', 'SH': '上海', 'JS': '江苏', 'ZJ': '浙江', 'AH': '安徽', 'FJ': '福建', 'JX': '江西', 'SD': '山东',
             'HA': '河南', 'HB': '湖北', 'HN': '湖南', 'GD': '广东', 'GX': '广西', 'HI': '海南', 'CQ': '重庆', 'SC': '四川', 'GZ': '贵州', 'YN': '云南', 'XZ': '西藏', 'SN': '陕西', 'GS': '甘肃', 'QH': '青海', 'NX': '宁夏', 'XJ': '新疆'}
# airport-name keywords that pick one airport in a multi-airport city
AIRPORT_KEYWORDS = {'首都': 'PEK', '大兴': 'PKX', '虹桥': 'SHA', '浦东': 'PVG', '双流': 'CTU', '天府': 'TFU', '新舟': 'ZYI', '茅台': 'WMT', '瑞金': 'RUG', '黄金': 'KOW', '腾湖': 'BFY'}


def minutes(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[2:])


def exclusive(dep):
    m = minutes(dep)
    return 480 < m <= 540 or 1140 <= m < 1200


def load_airports():
    # the curated base table lives in data/; src/assets/airports.json is generated from it,
    # so a rebuild never depends on its own previous output
    airports = json.loads((DATA.parent / 'airports/map-airports.json').read_text())
    for code, (name, city, province, lat, lon) in EXTRA_AIRPORTS.items():
        airports.setdefault(code, dict(iata=code, city=city, province=province, name=name, lat=lat, lon=lon))
    return airports


def load_ourairports():
    """Coordinates and province for airports the map table does not know yet (OurAirports, PDDL)."""
    path = ROOT / 'data/airports/ourairports-cn.csv'
    table = {}
    if path.exists():
        for r in csv.DictReader(path.open(encoding='utf-8')):
            lat, lon = map(float, r['coordinates'].split(','))
            if abs(lat) > 60:  # older dumps stored "lon, lat"
                lat, lon = lon, lat
            table.setdefault(r['iata_code'], dict(lat=lat, lon=lon, province=PROVINCES.get(r['iso_region'].split('-')[-1]), name_en=r['name']))
    return table


def airport_resolver(airports, cities):
    """Map (city code from the query, airport name from the result) to an entry of airports.json."""
    by_city_code = {}
    for c in cities:
        by_city_code.setdefault(c['iata'], c)
    official_airports = [c for c in cities if c['type'] == 'airport']
    ourairports = load_ourairports()
    strip = lambda s: re.sub(r'国际|机场|民航', '', s)
    cache = {}

    def add_airport(city_code, airport_name):
        """Create a map entry for an airport only the timetable names: IATA from the official location
        list, coordinates and province from OurAirports, Chinese names from the official data."""
        hit = next((a for a in official_airports if strip(a['name']) and strip(a['name']) in airport_name), None)
        code = hit['iata'] if hit else city_code
        geo = ourairports.get(code)
        if not geo or not geo['province']:
            return None
        city = by_city_code.get(city_code, {}).get('name') or by_city_code.get(code, {}).get('name') or airport_name
        airports[code] = dict(iata=code, city=city, province=geo['province'], name=airport_name, lat=geo['lat'], lon=geo['lon'])
        return airports[code]

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
        added = add_airport(city_code, airport_name)
        if added:
            cache[key] = added
            return added
        unresolved.add((city_code, airport_name))
        return None

    unresolved = set()
    resolve.unresolved = unresolved
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
            if not o or not d:
                continue
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
    if resolve.unresolved:
        sys.exit('cannot place these airports; add them to EXTRA_AIRPORTS or refresh data/airports/ourairports-cn.csv: ' + ', '.join(f'{n} (query city {c})' for c, n in sorted(resolve.unresolved)))
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
    if not valid:
        sys.exit('no timetable rows with a validity range in data/official/timetable/rows.jsonl; refusing to build empty assets')
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
