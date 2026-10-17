import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ferry import calmac, features, model, openmeteo
from ferry.routes import PORT_PAIRS, ROUTE_CODES

DAYS_AHEAD = 8


def main(model_path: Path, out_path: Path) -> None:
    today = datetime.now(ZoneInfo('Europe/London')).date()
    end = today + timedelta(days=DAYS_AHEAD)
    found = [s for origin, destination in PORT_PAIRS for s in calmac.sailings(origin, destination, today, end)]
    sailings = features.timetable(frame(found))
    hourly = features.local(openmeteo.forecast(today - timedelta(days=1), end))
    X = features.build(hourly, sailings)

    leads = (sailings.date - pd.Timestamp(today)).dt.days.to_numpy()
    risk = model.risk(model.load(model_path), X, leads)

    out_path.write_text(json.dumps({
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'sailings': entries(sailings, X.port_gust_window, risk),
    }, indent=1))


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


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
