import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from ferry import calmac, logbook, metoffice
from ferry.routes import PORT_PAIRS, ROUTE_CODES
DAYS_WATCHED = 8
SAILING_KEY = ('route_code', 'origin', 'destination', 'departs')
REMOVED = 'REMOVED'


def main(data_dir: Path) -> None:
    observed_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    today = datetime.now(ZoneInfo('Europe/London')).date()
    end = today + timedelta(days=DAYS_WATCHED)

    sailings = [logbook.row(s) for origin, destination in PORT_PAIRS for s in calmac.sailings(origin, destination, today, end)]
    gone = removed(logbook.read(data_dir / 'sailings.csv'), sailings, today, end)
    routes = {code: calmac.route(code) for code in ROUTE_CODES}
    notices = [logbook.row(n) for r in routes.values() for n in r.notices]
    vessels = [{'route_code': code, 'vessels': '; '.join(sorted(r.vessels))} for code, r in routes.items()]

    logged = {
        'sailings': logbook.record(data_dir / 'sailings.csv', sailings + gone, SAILING_KEY, observed_at),
        'notices': logbook.record(data_dir / 'notices.csv', notices, ('route_code', 'id'), observed_at),
        'vessels': logbook.record(data_dir / 'vessels.csv', vessels, ('route_code',), observed_at),
    }
    # The Met Office feed is extra, so if it's down the CalMac logs above still get written.
    try:
        warnings = [logbook.row(w) for w in metoffice.warnings()]
        logged['warnings'] = logbook.record(data_dir / 'warnings.csv', warnings, ('id',), observed_at)
    except requests.RequestException as error:
        print(f'Met Office warnings unavailable: {error}')
    print(f'{observed_at}: saw {len(sailings)} sailings ({len(gone)} newly removed) and {len(notices)} notices, logged changes {logged}')


def removed(logged: list[logbook.Row], observed: list[logbook.Row], start: date, end: date) -> list[logbook.Row]:
    """Logged sailings from `start` up to `end` that CalMac no longer lists, with status REMOVED.

    CalMac drops a cancelled sailing from its timetable rather than marking it CANCELLED, so a sailing that disappears is the only sign.
    """
    return [
        {**r, 'status': REMOVED}
        for r in logbook.missing(logged, observed, SAILING_KEY)
        if r['status'] != REMOVED and start.isoformat() <= r['sailing_date'] < end.isoformat()
    ]


if __name__ == '__main__':
    main(Path(sys.argv[1]))
