import re

import numpy as np
import pandas as pd

from ferry import calmac, logbook
from ferry.poll import REMOVED
from ferry.routes import ROUTE_CODES

WINDOWS = (1, 7, 28)
TITLE_DATE = re.compile(r'\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December)\b')


def cancellations(sailings: pd.DataFrame, outcomes: pd.DataFrame, days_before: np.ndarray | int) -> pd.DataFrame:
    """
    Each sailing's route's cancellations over the last 1, 7 and 28 days, counting back from `days_before` days before its date.
    `outcomes` has one row per past sailing with its `route`, `date` and whether it was `cancelled`; days without any read as quiet.
    """
    ending = sailings.date - pd.to_timedelta(days_before, unit='D')
    columns = {f'route_cancelled_{n}d': np.zeros(len(sailings)) for n in WINDOWS}
    daily = outcomes.groupby(['route', 'date']).cancelled.sum()
    for route, counts in daily.groupby(level='route'):
        counts = counts.droplevel('route')
        counts = counts.reindex(pd.date_range(counts.index.min(), max(counts.index.max(), ending.max())), fill_value=0)
        rows = (sailings.route == route).to_numpy()
        for n in WINDOWS:
            columns[f'route_cancelled_{n}d'][rows] = counts.rolling(n, min_periods=1).sum().reindex(ending[rows]).fillna(0).to_numpy()
    return pd.DataFrame(columns, index=sailings.index)


def observed(logged_sailings: list[logbook.Row], logged_notices: list[logbook.Row], before: str) -> pd.DataFrame:
    """
    What happened to every logged sailing dated before `before`, in the shape `cancellations` reads.
    A sailing is cancelled if CalMac stopped listing it or marked it cancelled. On a day with neither, every sailing counts as
    cancelled if a notice cancelled the whole day, which covers days from before the poll logged removed sailings.
    """
    latest = pd.DataFrame(logbook.latest(logged_sailings, ('route_code', 'origin', 'destination', 'departs')).values())
    if latest.empty:
        return pd.DataFrame({'route': [], 'date': pd.to_datetime([]), 'cancelled': []})
    latest = latest[(latest.sailing_date < before) & latest.route_code.isin(ROUTE_CODES)]
    marked = latest.status.isin(['CANCELLED', REMOVED])
    day = list(zip(latest.route_code, latest.sailing_date))
    marked_days = {d for d, m in zip(day, marked) if m}
    whole_days = cancelled_days(logged_notices, sorted({d for _, d in day}))
    cancelled = [m or (d not in marked_days and d in whole_days) for d, m in zip(day, marked)]
    return pd.DataFrame({
        'route': latest.route_code.map(ROUTE_CODES).to_numpy(),
        'date': pd.to_datetime(latest.sailing_date).to_numpy(),
        'cancelled': np.array(cancelled, dtype=int),
    })


def cancelled_days(logged_notices: list[logbook.Row], days: list[str]) -> set[tuple[str, str]]:
    """
    The (route code, UK date) pairs among `days` that a logged notice, as last seen, cancelled outright.
    A notice titled with a date, like "Friday 23 October", covers only that date, as CalMac often posts it the afternoon before.
    """
    notices = [calmac.Notice(**{k: v or None for k, v in r.items()}) for r in logbook.latest(logged_notices, ('route_code', 'id')).values()]
    return {
        (n.route_code, d)
        for n in notices
        if n.status == 'SAILING' and n.sub_status == 'ALL_SAILINGS_CANCELLED'
        for d in days
        if (titled_day(n) == d if titled_day(n) else calmac.covers(n, d))
    }


def titled_day(notice: calmac.Notice) -> str | None:
    """The UK date a notice's title names, such as "Friday 23 October", in the year it ends, if it names one."""
    found = TITLE_DATE.search(notice.title or '')
    if not found or not notice.ends:
        return None
    return pd.to_datetime(f'{found[1]} {found[2]} {pd.Timestamp(notice.ends).year}', format='%d %B %Y').date().isoformat()
