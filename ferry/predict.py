import hashlib
import json
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ferry import calmac, features, logbook, model, openmeteo
from ferry.routes import PORT_PAIRS, ROUTE_CODES

DAYS_AHEAD = 8
LOG_KEY = ('origin', 'destination', 'departs')
SEVERITY = ['NORMAL', 'BE_AWARE', 'DISRUPTIONS', 'ALL_SAILINGS_CANCELLED']


def main(model_path: Path, out_path: Path, log_path: Path | None) -> None:
    generated_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    today = datetime.now(ZoneInfo('Europe/London')).date()
    end = today + timedelta(days=DAYS_AHEAD)
    found = [s for origin, destination in PORT_PAIRS for s in calmac.sailings(origin, destination, today, end)]
    sailings = features.timetable(frame(found))
    hourly = features.local(openmeteo.forecast(today - timedelta(days=1), end))
    X = features.build(hourly, sailings)

    leads = (sailings.date - pd.Timestamp(today)).dt.days.to_numpy()
    risk = model.risk(model.load(model_path), X, leads)

    rows = entries(sailings, X.port_gust_window, risk)
    notices = {code: calmac.route(code).notices for code in ROUTE_CODES}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({'generated_at': generated_at, 'sailings': rows, 'routes': routes(notices, generated_at)}, indent=1))

    if log_path:
        model_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()[:12]
        logbook.record(log_path, log_rows(rows, today, model_sha256), LOG_KEY, generated_at)


def frame(found: list[calmac.Sailing]) -> pd.DataFrame:
    """CalMac's sailings in the shape `features.timetable` expects, keeping the fields the page shows."""
    table = pd.DataFrame([asdict(s) for s in found])
    table = table[table.route_code.isin(ROUTE_CODES)]
    departs = pd.to_datetime(table.departs, utc=True)
    return table.assign(
        departs_at=table.departs,
        departs=departs.dt.tz_convert('Europe/London').dt.tz_localize(None),
        route=table.route_code.map(ROUTE_CODES),
        from_brodick=table.origin.eq('Brodick').astype(int),
        passage_mins=(pd.to_datetime(table.arrives, utc=True) - departs).dt.total_seconds() / 60,
    )


def entries(sailings: pd.DataFrame, gusts: pd.Series, risk: np.ndarray) -> list[dict]:
    """One entry per sailing for the page. CalMac's own cancellations take the place of a prediction."""
    rows = []
    for s, gust, cancellation_risk in zip(sailings.itertuples(), gusts, risk):
        predicted = s.status != 'CANCELLED'
        rows.append({
            'origin': s.origin,
            'destination': s.destination,
            'departs': s.departs_at,
            'arrives': s.arrives,
            'rescheduled_departs': None if pd.isna(s.rescheduled_departs) else s.rescheduled_departs,
            'status': s.status,
            'gust_knots': None if pd.isna(gust) else round(float(gust)),
            'chance_of_sailing': round(1 - float(cancellation_risk), 3) if predicted else None,
        })
    return sorted(rows, key=lambda r: r['departs'])


def routes(notices: dict[str, list[calmac.Notice]], now: str) -> list[dict]:
    """Each route's status and the sailing notices behind it. A route is as disrupted as its worst live notice."""
    rows = []
    for code, found in notices.items():
        live = [n for n in found if n.status == 'SAILING' and n.sub_status in SEVERITY[1:] and _live(n, now)]
        live.sort(key=lambda n: (SEVERITY.index(n.sub_status), n.updated_at), reverse=True)
        rows.append({
            'route': ROUTE_CODES[code],
            'status': live[0].sub_status if live else 'NORMAL',
            'notices': [{
                'title': n.title,
                'status': n.sub_status,
                'reason': n.disruption_reason.strip() if n.disruption_reason else None,
                'updated_at': n.updated_at,
                'detail': n.detail,
            } for n in live],
        })
    return rows


def _live(notice: calmac.Notice, now: str) -> bool:
    return pd.Timestamp(notice.starts) <= pd.Timestamp(now) < pd.Timestamp(notice.ends)


def log_rows(entries: list[dict], today: date, model_sha256: str) -> list[logbook.Row]:
    """The page's entries as rows for the predictions log, with each sailing's days ahead and the model that scored it."""
    rows = []
    for e in entries:
        departs_on = datetime.fromisoformat(e['departs']).astimezone(ZoneInfo('Europe/London')).date()
        rows.append({k: '' if v is None else str(v) for k, v in {
            'origin': e['origin'],
            'destination': e['destination'],
            'departs': e['departs'],
            'days_ahead': (departs_on - today).days,
            'status': e['status'],
            'gust_knots': e['gust_knots'],
            'chance_of_sailing': e['chance_of_sailing'],
            'model_sha256': model_sha256,
        }.items()})
    return rows


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
