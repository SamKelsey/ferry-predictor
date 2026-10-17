import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from ferry import calmac, logbook

PORT_PAIRS = [('Ardrossan', 'Brodick'), ('Brodick', 'Ardrossan'), ('Troon', 'Brodick'), ('Brodick', 'Troon')]
ROUTE_CODES = ['003', '301']
DAYS_WATCHED = 8


def main(data_dir: Path) -> None:
    observed_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    today = datetime.now(ZoneInfo('Europe/London')).date()
    end = today + timedelta(days=DAYS_WATCHED)

    sailings = [logbook.row(s) for origin, destination in PORT_PAIRS for s in calmac.sailings(origin, destination, today, end)]
    routes = {code: calmac.route(code) for code in ROUTE_CODES}
    notices = [logbook.row(n) for r in routes.values() for n in r.notices]
    vessels = [{'route_code': code, 'vessels': '; '.join(sorted(r.vessels))} for code, r in routes.items()]

    logged = {
        'sailings': logbook.record(data_dir / 'sailings.csv', sailings, ('route_code', 'origin', 'destination', 'departs'), observed_at),
        'notices': logbook.record(data_dir / 'notices.csv', notices, ('route_code', 'id'), observed_at),
        'vessels': logbook.record(data_dir / 'vessels.csv', vessels, ('route_code',), observed_at),
    }
    print(f'{observed_at}: saw {len(sailings)} sailings and {len(notices)} notices, logged changes {logged}')


if __name__ == '__main__':
    main(Path(sys.argv[1]))
