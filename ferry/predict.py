import hashlib
import json
import sys
from dataclasses import asdict
from bisect import bisect_right
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ferry import calmac, features, history, logbook, model, openmeteo
from ferry.routes import PORT_PAIRS, ROUTE_CODES

DAYS_AHEAD = 8
# How many days before today the page gets each sailing's hourly predictions for, to chart how they moved.
HISTORY_DAYS = 7
LOG_KEY = ('origin', 'destination', 'departs')
SEVERITY = ['NORMAL', 'BE_AWARE', 'DISRUPTIONS', 'ALL_SAILINGS_CANCELLED']


def main(model_path: Path, out_path: Path, log_path: Path | None, data_dir: Path | None = None) -> None:
    """Predicts the next days' sailings into `out_path`, learning recent cancellations from the poll's logs in `data_dir` if given."""
    generated_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    today = datetime.now(ZoneInfo('Europe/London')).date()
    end = today + timedelta(days=DAYS_AHEAD)
    notices = {code: calmac.route(code).notices for code in ROUTE_CODES}
    found = [s for origin, destination in PORT_PAIRS for s in calmac.sailings(origin, destination, today, end)]
    logged_sailings = logbook.read(data_dir / 'sailings.csv') if data_dir else []
    logged_notices = logbook.read(data_dir / 'notices.csv') if data_dir else []
    found += dropped(logged_sailings, found, notices, today, end)
    sailings = features.timetable(frame(found))
    hourly = features.local(openmeteo.forecast(today - timedelta(days=1), end))
    leads = (sailings.date - pd.Timestamp(today)).dt.days.to_numpy()
    X = features.build(hourly, sailings, history.observed(logged_sailings, logged_notices, today.isoformat()), leads)

    risk = model.risk(model.load(model_path), X, leads)

    rows = entries(sailings, X.port_gust_window, risk)
    # Logged first, so the history includes the predictions being published now.
    if log_path:
        model_sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()[:12]
        logbook.record(log_path, log_rows(rows, today, model_sha256), LOG_KEY, generated_at)
    earlier = hourly_history(logbook.read(log_path), datetime.fromisoformat(generated_at)) if log_path else {}
    for row in rows:
        row['history'] = earlier.get(tuple(row[k] for k in LOG_KEY), [])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({'generated_at': generated_at, 'sailings': rows, 'routes': routes(notices, generated_at)}, indent=1))


def dropped(logged: list[logbook.Row], found: list[calmac.Sailing], notices: dict[str, list[calmac.Notice]], today: date, end: date) -> list[calmac.Sailing]:
    """
    Sailings CalMac took out of its timetable on days it cancelled outright, as last logged and marked cancelled.
    CalMac drops a cancelled day's sailings rather than marking them, which would otherwise make the day vanish.
    """
    cancelled = {
        (code, day)
        for code, found_notices in notices.items()
        for n in found_notices
        if n.status == 'SAILING' and n.sub_status == 'ALL_SAILINGS_CANCELLED'
        for day in _days(n, today, end)
    }
    seen = {(s.origin, s.destination, s.departs) for s in found}
    latest = {(r['origin'], r['destination'], r['departs']): r for r in logged}
    return [
        calmac.Sailing(
            sailing_date=r['sailing_date'],
            route_code=r['route_code'],
            origin=r['origin'],
            destination=r['destination'],
            departs=r['departs'],
            arrives=r['arrives'],
            rescheduled_departs=None,
            status='CANCELLED',
        )
        for key, r in latest.items()
        if (r['route_code'], r['sailing_date']) in cancelled and key not in seen
    ]


def _days(notice: calmac.Notice, today: date, end: date) -> list[str]:
    """The UK dates from `today` up to `end` that a notice covers."""
    days = [d.date().isoformat() for d in pd.date_range(today, end - timedelta(days=1))]
    return [d for d in days if calmac.covers(notice, d)]


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


def hourly_history(logged: list[logbook.Row], now: datetime) -> dict[tuple[str, ...], list[dict]]:
    """
    Each logged sailing's chance of sailing as the page showed it at the end of every UK hour, from `HISTORY_DAYS` days
    before `now` up to `now`, grouped by day, oldest first. The log only gains a row when a prediction changes, so each hour
    takes the latest row up to its end. Hours before the sailing was first predicted, or after CalMac cancelled it, are skipped.
    """
    uk = ZoneInfo('Europe/London')
    today = now.astimezone(uk).date()
    days = [today - timedelta(days=n) for n in range(HISTORY_DAYS, -1, -1)]
    by_sailing: dict[tuple[str, ...], list[logbook.Row]] = {}
    for r in sorted(logged, key=lambda r: r['observed_at']):
        by_sailing.setdefault(tuple(r[k] for k in LOG_KEY), []).append(r)
    history = {}
    for key, rows in by_sailing.items():
        made = [datetime.fromisoformat(r['observed_at']) for r in rows]
        sailing_days = []
        for day in days:
            chances = []
            for hour in range(24):
                if datetime.combine(day, time(hour), uk) > now:
                    break
                shown = bisect_right(made, min(datetime.combine(day, time(hour, 59, 59), uk), now)) - 1
                if shown >= 0 and rows[shown]['chance_of_sailing']:
                    chances.append(float(rows[shown]['chance_of_sailing']))
            if chances:
                sailing_days.append({'date': day.isoformat(), 'chances': chances})
        history[key] = sailing_days
    return history


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
    """Each route's status and the sailing notices behind it, including ones not up yet. A route is as disrupted as its worst notice."""
    rows = []
    for code, found in notices.items():
        live = [n for n in found if n.status == 'SAILING' and n.sub_status in SEVERITY[1:] and pd.Timestamp(now) < pd.Timestamp(n.ends)]
        live.sort(key=lambda n: (SEVERITY.index(n.sub_status), n.updated_at), reverse=True)
        rows.append({
            'route': ROUTE_CODES[code],
            'status': live[0].sub_status if live else 'NORMAL',
            'notices': [{
                'title': n.title,
                'status': n.sub_status,
                'reason': n.disruption_reason.strip() if n.disruption_reason else None,
                'starts': n.starts,
                'ends': n.ends,
                'updated_at': n.updated_at,
                'detail': n.detail,
            } for n in live],
        })
    return rows


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
    main(Path(sys.argv[1]), Path(sys.argv[2]), *(Path(a) for a in sys.argv[3:5]))
