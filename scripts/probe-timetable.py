"""Probe the official timetable for schedules beyond what the repository already covers.

The timetable only shows the current IATA season (e.g. 2026-03-29 to 2026-10-24). This probe
queries a handful of busy city pairs and reports the latest validity date it sees, so a
scheduled job can notice when the next season's schedule has been loaded.

Usage: python scripts/probe-timetable.py [--rate N]
Prints a JSON summary; writes new_season / max_valid_to / covered_to to $GITHUB_OUTPUT when set.
Exit code is 0 unless no pair answered (the site is unreachable).
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('crawler', ROOT / 'scripts/crawl-official-timetable.py')
crawler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crawler)

# busy pairs across the group's hubs; the first direction of each is enough
PROBE_PAIRS = [('BJS', 'HAK'), ('BJS', 'HGH'), ('BJS', 'URC'), ('SHA', 'HAK'), ('CAN', 'BJS'), ('CTU', 'BJS'), ('TSN', 'HAK'), ('XIY', 'URC'), ('SZX', 'BJS'), ('KMG', 'BJS')]


def main(argv):
    rate = float(argv[argv.index('--rate') + 1]) if '--rate' in argv else 15
    cities = json.loads((ROOT / 'data/official/timetable/cities.json').read_text())
    by_iata = {}
    for c in cities:
        by_iata.setdefault(c['iata'], c)
    covered_to = json.loads((ROOT / 'src/assets/coverage.json').read_text())['valid_to']
    session = crawler.Session()
    answered, max_valid, rows_total, per_pair = 0, '', 0, {}
    for a, b in PROBE_PAIRS:
        status, rows, _ = crawler.query(session, by_iata[a], by_iata[b])
        per_pair[f'{a}-{b}'] = status
        if status in ('ok', 'none'):
            answered += 1
        for x in rows:
            rows_total += 1
            end = x['validity'].split('-')[1].replace('.', '-') if x['validity'] else ''
            max_valid = max(max_valid, end)
        time.sleep(60 / rate)
    result = {'answered_pairs': answered, 'probe_pairs': len(PROBE_PAIRS), 'rows_seen': rows_total, 'max_valid_to': max_valid, 'covered_to': covered_to,
              'new_season': bool(max_valid and max_valid > covered_to), 'pairs': per_pair}
    print(json.dumps(result, ensure_ascii=False))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"new_season={'true' if result['new_season'] else 'false'}\nmax_valid_to={max_valid}\ncovered_to={covered_to}\n")
    if not answered:
        sys.exit('no probe pair answered; the timetable site is unreachable from here')


if __name__ == '__main__':
    main(sys.argv[1:])
