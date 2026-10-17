import time
from datetime import date

import pandas as pd
import requests

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ARCHIVE_URL = 'https://historical-forecast-api.open-meteo.com/v1/forecast'
PREVIOUS_RUNS_URL = 'https://previous-runs-api.open-meteo.com/v1/forecast'
POINTS = {'troon': (55.55, -4.68), 'ardrossan': (55.64, -4.82), 'firth': (55.60, -4.95)}
VARIABLES = ['wind_speed_10m', 'wind_gusts_10m', 'wind_direction_10m', 'pressure_msl']
LEADS = range(1, 8)


def forecast(start: date, end: date) -> pd.DataFrame:
    """The latest GFS forecast, hourly in UTC, for every point from `start` to `end` inclusive."""
    return _hourly(FORECAST_URL, VARIABLES, start, end)


def archive(start: date, end: date) -> pd.DataFrame:
    """The GFS forecasts made shortly before each hour, hourly in UTC, from `start` to `end` inclusive."""
    return pd.concat([_hourly(ARCHIVE_URL, VARIABLES, first, last) for first, last in _years(start, end)])


def previous_runs(start: date, end: date) -> dict[int, pd.DataFrame]:
    """For each lead of 1 to 7 days, the GFS forecasts made that many days before each hour, hourly in UTC."""
    variables = [f'{v}_previous_day{lead}' for lead in LEADS for v in VARIABLES]
    hourly = pd.concat([_hourly(PREVIOUS_RUNS_URL, variables, first, last) for first, last in _years(start, end)])
    return {
        lead: hourly.filter(regex=f'_previous_day{lead}$').rename(columns=lambda c: c.removesuffix(f'_previous_day{lead}'))
        for lead in LEADS
    }


def _years(start: date, end: date) -> list[tuple[date, date]]:
    return [(max(start, date(year, 1, 1)), min(end, date(year, 12, 31))) for year in range(start.year, end.year + 1)]


def _hourly(url: str, variables: list[str], start: date, end: date) -> pd.DataFrame:
    frames = []
    for name, (latitude, longitude) in POINTS.items():
        body = _get(url, {
            'latitude': latitude,
            'longitude': longitude,
            'hourly': ','.join(variables),
            'models': 'gfs_seamless',
            'wind_speed_unit': 'kn',
            'timezone': 'UTC',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
        })
        frame = pd.DataFrame(body['hourly'])
        frame = frame.set_index(pd.to_datetime(frame.pop('time')))
        frames.append(frame.add_prefix(f'{name}_'))
    return pd.concat(frames, axis=1)


def _get(url: str, params: dict[str, object], attempts: int = 5) -> dict:
    for attempt in range(attempts):
        body = requests.get(url, params=params, timeout=240).json()
        if 'hourly' in body:
            return body
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'Open-Meteo gave no data: {body}')
