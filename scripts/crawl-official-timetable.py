"""Crawl the official Hainan Airlines timetable (new.hnair.com flightSchedule) by city pair.

Only the public, login-free timetable page is used. Every row is kept verbatim as the
page shows it (flight number, departure/arrival time, weekday marks, validity text).
No third-party schedule is read and nothing is inferred.

Usage:
  python scripts/crawl-official-timetable.py cities            # refresh the city list only
  python scripts/crawl-official-timetable.py crawl [options]    # crawl pairs, resumable
  python scripts/crawl-official-timetable.py summary            # statistics of rows.jsonl

Options for crawl:
  --pairs 2025      ordered pairs that appear in the official 2025 reference table, both directions (default)
  --pairs matrix    every ordered pair among the cities of the 2025 table (large)
  --origin HGH      only pairs leaving this IATA city code (combine with --pairs)
  --dest PEK        only pairs arriving at this IATA city code
  --pair HGH-DLC,HGH-HRB   query exactly these pairs (IATA city/airport codes) instead of the seed list
  --limit N         stop after N new queries
  --delay SECONDS   pause between queries (default 0.8)
  --refresh         re-query pairs that already have a result in rows.jsonl

Output (data/official/timetable/):
  cities.json   official location list (Chinese name, IATA, location id)
  rows.jsonl    one JSON object per query: pair, fetched_at and the parsed rows
  raw/          the result block of every query as returned by the site (git-ignored)
"""
import json
import re
import sys
import time
import html
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/official/timetable'
RAW = OUT / 'raw'
BASE = 'https://new.hnair.com/hainanair/ibe'
PAGE = BASE + '/common/flightSchedule.do'
QUERY = BASE + '/air/processFlightSchedule.do'
LOCATIONS = BASE + '/hierarchylocationsearch.do?&language=zh&searchableOnly=true&format=json&locationType=airport&locationType=city&ajaxSearch='
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
# the official 2025 table names some airports instead of cities; the timetable is queried per city
CITY_OF_AIRPORT_NAME = {'北京首都': '北京', '北京大兴': '北京', '上海浦东': '上海', '上海虹桥': '上海', '成都天府': '成都', '重庆万州': '万州', '重庆江北': '重庆', '大连周水子': '大连',
                        '茅台': '遵义', '那拉提': '新源', '香格里拉': '迪庆', '达州': '达州金垭'}


class Session:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [('User-Agent', UA), ('Accept-Language', 'zh-CN,zh;q=0.9')]
        self.open_page()

    def open_page(self):
        self.get(PAGE)

    def get(self, url, tries=4):
        for i in range(tries):
            try:
                with self.opener.open(url, timeout=60) as r:
                    return r.read().decode('utf-8', 'replace')
            except Exception as e:  # network resets are common through proxies; back off and retry
                if i == tries - 1:
                    raise
                time.sleep(2 ** i)

    def post(self, url, fields, tries=4):
        data = urllib.parse.urlencode(fields).encode()
        for i in range(tries):
            try:
                req = urllib.request.Request(url, data=data, headers={'Referer': PAGE, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded'})
                with self.opener.open(req, timeout=90) as r:
                    return r.read().decode('utf-8', 'replace')
            except Exception:
                if i == tries - 1:
                    raise
                time.sleep(2 ** i)


def fetch_cities(session):
    """Enumerate the site's own location database: domestic cities, plus airports as a fallback
    for places the database only knows as an airport (e.g. 达州金垭)."""
    found = {}
    for q in 'abcdefghijklmnopqrstuvwxyz':
        data = json.loads(session.get(LOCATIONS + q))
        for loc in data.get('Locations', []):
            if loc.get('Country') != 'CN' or loc.get('LocationType') not in ('city', 'airport'):
                continue
            iata = next((c['Value'] for c in loc.get('Codes', []) if c['Context'] == 'IATA'), None)
            names = {n['Language']: n['Name'] for n in loc.get('Names', [])}
            # 'zh' holds the simplified name, 'cn' the traditional one
            if iata:
                found[loc['Id']] = {'id': loc['Id'], 'type': loc['LocationType'], 'iata': iata, 'name': names.get('zh') or names.get('cn') or loc.get('Name'), 'name_traditional': names.get('cn'), 'name_en': loc.get('Name'), 'lat': loc.get('Lat'), 'lng': loc.get('Lng')}
        time.sleep(0.3)
    return sorted(found.values(), key=lambda c: (c['type'] != 'city', c['iata']))


def result_block(page):
    """The ajax answer is a whole page; keep only the result container (up to the footer)."""
    m = re.search(r'<div id="flightScheduleSearchResult">.*?(?=<div class="footer|</body>)', page, re.S)
    return m.group(0) if m else None


def parse_result(page):
    """Return (status, rows). status: 'ok' | 'none' | 'session' | 'unknown'."""
    block = result_block(page)
    if block is None:
        if '会话已经超时' in page or 'processLogin' in page:
            return 'session', []
        return 'unknown', []
    if 'class="no-result"' in block:
        return 'none', []
    rows = []
    pair = None
    # the block is a sequence of airport-pair headers and table items; walk it in order
    for kind, chunk in re.findall(r'<div class="(search-airport|table-item)">(.*?)(?=<div class="search-airport">|<div class="table-item">|$)', block, re.S):
        if kind == 'search-airport':
            pair = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<div class="search-airport-notice">.*', '', chunk, flags=re.S))).strip()
            pair = re.sub(r'<[^>]+>', '', pair).strip()
            continue
        cell = lambda cls: re.search(r'<div class="%s">(.*?)</div>' % cls, chunk, re.S)
        fn = cell('flight-number')
        logo = re.search(r'logo_([A-Z0-9]{2})\.png', fn.group(1)) if fn else None
        flight_text = html.unescape(re.sub(r'<[^>]+>', ' ', fn.group(1))).strip() if fn else ''
        flight_no = re.search(r'\b([A-Z0-9]{2}\d{3,4})\b', flight_text)
        days = re.findall(r'<div class="period-day">(.*?)</div>', chunk, re.S)
        validity = re.search(r'(\d{4}\.\s*\d{2}\.\s*\d{2}\s*-\s*\d{4}\.\s*\d{2}\.\s*\d{2})', chunk)
        rows.append({
            'airport_pair': pair,
            'flight_no': flight_no.group(1) if flight_no else flight_text,
            'flight_cell_text': flight_text,
            'logo_carrier': logo.group(1) if logo else None,
            'dep_time': re.sub(r'\s+', '', cell('departure-time').group(1)) if cell('departure-time') else None,
            'arr_time': re.sub(r'\s+', '', cell('arrive-time').group(1)) if cell('arrive-time') else None,
            'days': ''.join(str(i + 1) for i, d in enumerate(days) if 'icon-aircraft' in d),
            'day_cells': len(days),
            'validity': re.sub(r'\s+', '', validity.group(1)) if validity else None,
        })
    return 'ok', rows


def query(session, origin, dest):
    fields = {
        'Search/AirlineMode': 'false', 'Search/calendarCacheSearchDays': '60', 'Search/calendarSearched': 'false', 'dropOffLocationRequired': 'false',
        'Search/searchType': 'F', 'searchTypeValidator': 'F', 'xSellMode': 'false', 'Search/flightType': '', 'destinationLocationSearchBoxType': 'L',
        'Search/AirDirectOnly': '0', 'Search/seatClass': 'A',
        # location_type tells the site whether the id is a (multi-airport) city or a single airport
        'Search/OriginDestinationInformation/Origin/location': origin['id'], 'Search/OriginDestinationInformation/Origin/location_type': str(origin['type'] == 'city').lower(), 'Search/OriginDestinationInformation/Origin/location_input': origin['name'],
        'Search/OriginDestinationInformation/Destination/location': dest['id'], 'Search/OriginDestinationInformation/Destination/location_type': str(dest['type'] == 'city').lower(), 'Search/OriginDestinationInformation/Destination/location_input': dest['name'],
    }
    page = session.post(QUERY, fields)
    status, rows = parse_result(page)
    if status == 'session':
        session.open_page()
        page = session.post(QUERY, fields)
        status, rows = parse_result(page)
    return status, rows, page


def load_cities():
    path = OUT / 'cities.json'
    if not path.exists():
        sys.exit('cities.json missing; run: python scripts/crawl-official-timetable.py cities')
    return json.loads(path.read_text())


def seed_pairs(cities, mode):
    # cities come first in the list, so a city entry wins over an airport with the same name/code
    by_name, by_iata = {}, {}
    for c in cities:
        by_name.setdefault(c['name'], c); by_iata.setdefault(c['iata'], c)
    raw = json.loads((ROOT / 'data/official/official-2025-raw.json').read_text())
    unresolved = set()

    def city(name):
        c = by_name.get(CITY_OF_AIRPORT_NAME.get(name, name))
        if not c:
            unresolved.add(name)
        return c

    table_cities = sorted({c['iata'] for r in raw for c in (city(r[1]), city(r[2])) if c})
    if unresolved:
        print('not in the official location list, skipped:', '、'.join(sorted(unresolved)), file=sys.stderr)
    if mode == 'matrix':
        return [(by_iata[a], by_iata[b]) for a in table_cities for b in table_cities if a != b]
    pairs = set()
    for r in raw:
        o, d = city(r[1]), city(r[2])
        if o and d and o['iata'] != d['iata']:
            pairs.add((o['iata'], d['iata'])); pairs.add((d['iata'], o['iata']))
    return [(by_iata[a], by_iata[b]) for a, b in sorted(pairs)]


def minutes(t):
    h, m = t.split(':')
    return int(h) * 60 + int(m)


def summary():
    recs = [json.loads(l) for l in (OUT / 'rows.jsonl').read_text().splitlines() if l.strip()]
    latest = {}
    for r in recs:  # the last answer for a pair wins
        latest[(r['origin'], r['dest'])] = r
    rows = [dict(x, origin=r['origin'], dest=r['dest']) for r in latest.values() for x in r['rows']]
    status = {}
    for r in latest.values():
        status[r['status']] = status.get(r['status'], 0) + 1
    carriers = {}
    for x in rows:
        carriers[x['logo_carrier'] or x['flight_no'][:2]] = carriers.get(x['logo_carrier'] or x['flight_no'][:2], 0) + 1
    evening = [x for x in rows if x['dep_time'] and (minutes(x['dep_time']) >= 19 * 60 or minutes(x['dep_time']) <= 9 * 60)]
    print(json.dumps({
        'pairs_queried': len(latest), 'pair_status': status, 'schedule_rows': len(rows),
        'distinct_flights': len({x['flight_no'] for x in rows}),
        'distinct_airport_pairs': len({x['airport_pair'] for x in rows}),
        'rows_by_carrier_logo': dict(sorted(carriers.items(), key=lambda kv: -kv[1])),
        'rows_departing_19_00_to_09_00': len(evening),
        'flight_cells_with_extra_text': sorted({x['flight_cell_text'] for x in rows if x['flight_cell_text'] != x['flight_no']})[:20],
        'rows_without_validity': sum(1 for x in rows if not x['validity']),
        'rows_without_7_day_cells': sum(1 for x in rows if x['day_cells'] != 7),
        'fetched_between': [min(r['fetched_at'] for r in latest.values()), max(r['fetched_at'] for r in latest.values())],
    }, ensure_ascii=False, indent=1))


def main(argv):
    OUT.mkdir(parents=True, exist_ok=True); RAW.mkdir(exist_ok=True)
    cmd = argv[0] if argv else 'crawl'
    if cmd == 'summary':
        return summary()
    opts = dict(zip(argv[1::2], argv[2::2])) if cmd == 'crawl' else {}
    flags = set(a for a in argv[1:] if a.startswith('--') and a not in opts)
    session = Session()
    if cmd == 'cities':
        cities = fetch_cities(session)
        (OUT / 'cities.json').write_text(json.dumps(cities, ensure_ascii=False, indent=0))
        print(f'{len(cities)} domestic cities saved')
        return
    cities = load_cities()
    if '--pair' in opts:
        by_iata = {}
        for c in cities:
            by_iata.setdefault(c['iata'], c)
        pairs = [(by_iata[a], by_iata[b]) for a, b in (x.split('-') for x in opts['--pair'].split(','))]
    else:
        pairs = seed_pairs(cities, opts.get('--pairs', '2025'))
    if '--origin' in opts:
        pairs = [p for p in pairs if p[0]['iata'] == opts['--origin']]
    if '--dest' in opts:
        pairs = [p for p in pairs if p[1]['iata'] == opts['--dest']]
    rows_path = OUT / 'rows.jsonl'
    done = set()
    if rows_path.exists() and '--refresh' not in flags:
        for line in rows_path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec['status'] in ('ok', 'none'):
                    done.add((rec['origin'], rec['dest']))
    todo = [p for p in pairs if (p[0]['iata'], p[1]['iata']) not in done]
    limit = int(opts.get('--limit', len(todo)))
    delay = float(opts.get('--delay', 0.8))
    print(f'{len(pairs)} pairs, {len(done)} already done, querying {min(limit, len(todo))}')
    counts = {'ok': 0, 'none': 0, 'unknown': 0, 'rows': 0}
    with rows_path.open('a') as out:
        for n, (o, d) in enumerate(todo[:limit], 1):
            try:
                status, rows, page = query(session, o, d)
            except Exception as e:
                status, rows, page = 'error', [], str(e)
            key = f'{o["iata"]}-{d["iata"]}'
            (RAW / f'{key}.html').write_text(result_block(page) or page)
            rec = {'origin': o['iata'], 'dest': d['iata'], 'origin_name': o['name'], 'dest_name': d['name'], 'origin_id': o['id'], 'dest_id': d['id'], 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'status': status, 'rows': rows}
            out.write(json.dumps(rec, ensure_ascii=False) + '\n'); out.flush()
            counts[status] = counts.get(status, 0) + 1; counts['rows'] += len(rows)
            print(f'[{n}/{min(limit, len(todo))}] {key} {o["name"]}→{d["name"]}: {status} {len(rows)} rows', flush=True)
            if status in ('unknown', 'error'):
                time.sleep(5); session = Session()
            time.sleep(delay)
    print(json.dumps(counts))


if __name__ == '__main__':
    main(sys.argv[1:])
