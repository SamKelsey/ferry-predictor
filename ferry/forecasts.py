import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from ferry import openmeteo

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ENSEMBLE_URL = 'https://ensemble-api.open-meteo.com/v1/ensemble'
MARINE_URL = 'https://marine-api.open-meteo.com/v1/marine'
DAYS = 8
# ECMWF and the wave model forecast every 3 hours; Open-Meteo fills the hours between by interpolation.
STEP_HOURS = 3
GUST_THRESHOLDS = (30, 35, 40)
# The runs that forecast a full 8 days. ECMWF's 06:00 and 18:00 runs stop sooner, so Open-Meteo pads them from an older run.
RUN_HOURS = (0, 12)
WIND = ['wind_speed_10m', 'wind_gusts_10m', 'wind_direction_10m']


def main(data_dir: Path) -> None:
    """Saves the latest run of each forecast source under `data_dir`/forecasts, one CSV per 00:00 or 12:00 run, each only once."""
    for name, (latest_run, fetch) in SOURCES.items():
        run = latest_run()
        path = data_dir / 'forecasts' / name / f'{run:%Y-%m-%dT%H}.csv'
        if run.hour not in RUN_HOURS:
            print(f'{name}: latest run {run:%Y-%m-%d %H}Z is not a full-length run')
            continue
        if path.exists():
            print(f'{name}: run {run:%Y-%m-%d %H}Z already saved')
            continue
        rows = fetch(run)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(path, index=False)
        print(f'{name}: saved run {run:%Y-%m-%d %H}Z, {len(rows)} rows')


def latest_run(meta_url: str) -> datetime:
    """When the newest complete run of a model on Open-Meteo started, from its metadata."""
    meta = requests.get(meta_url, timeout=60).json()
    return datetime.fromtimestamp(meta['last_run_initialisation_time'], timezone.utc)


def ecmwf(run: datetime) -> pd.DataFrame:
    """ECMWF's main forecast of wind, gusts and pressure at each point."""
    return _points(FORECAST_URL, {'models': 'ecmwf_ifs025', 'hourly': ','.join([*WIND, 'pressure_msl'])}, run, as_is)


def ecmwf_ensemble(run: datetime) -> pd.DataFrame:
    """How ECMWF's 51 ensemble forecasts of wind and gusts spread at each point."""
    return _points(ENSEMBLE_URL, {'models': 'ecmwf_ifs025', 'hourly': ','.join(WIND)}, run, ensemble_summary)


def waves(run: datetime) -> pd.DataFrame:
    """Météo-France's forecast of waves and swell at each point."""
    variables = 'wave_height,wave_direction,wave_period,swell_wave_height'
    return _points(MARINE_URL, {'models': 'meteofrance_wave', 'hourly': variables}, run, as_is)


def as_is(hourly: pd.DataFrame) -> pd.DataFrame:
    return hourly


def ensemble_summary(hourly: pd.DataFrame) -> pd.DataFrame:
    """Each hour's spread across ensemble members: gust quantiles, the share of members over each gust threshold, and wind direction."""
    wind, gust, direction = (hourly.filter(regex=f'^{v}(_member\\d+)?$').to_numpy() for v in WIND)
    radians = np.deg2rad(direction)
    east, north = np.sin(radians).mean(axis=1), np.cos(radians).mean(axis=1)
    summary = pd.DataFrame({
        'members': gust.shape[1],
        'gust_p10': np.percentile(gust, 10, axis=1),
        'gust_p50': np.percentile(gust, 50, axis=1),
        'gust_p90': np.percentile(gust, 90, axis=1),
        'gust_max': gust.max(axis=1),
        **{f'gust_over_{t}': (gust > t).mean(axis=1) for t in GUST_THRESHOLDS},
        'wind_p50': np.percentile(wind, 50, axis=1),
        'direction': np.rad2deg(np.arctan2(east, north)) % 360,
        'direction_agreement': np.hypot(east, north),
    }, index=hourly.index)
    return summary.round(3)


def point_rows(hourly: dict, point: str, run: datetime, summarise: Callable[[pd.DataFrame], pd.DataFrame]) -> pd.DataFrame:
    """One point's forecast from `run` onward, every `STEP_HOURS`, with how many hours ahead of the run each row is."""
    frame = pd.DataFrame(hourly)
    times = pd.to_datetime(frame.pop('time'), utc=True)
    keep = (times >= run) & (times.dt.hour % STEP_HOURS == 0)
    frame, times = frame[keep.to_numpy()].reset_index(drop=True), times[keep].reset_index(drop=True)
    return pd.concat([pd.DataFrame({
        'run': f'{run:%Y-%m-%dT%H:%M}Z',
        'point': point,
        'time': times.dt.strftime('%Y-%m-%dT%H:%MZ'),
        'lead_hours': ((times - run).dt.total_seconds() // 3600).astype(int),
    }), summarise(frame).reset_index(drop=True)], axis=1)


def _points(url: str, params: dict[str, object], run: datetime, summarise: Callable[[pd.DataFrame], pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name, (latitude, longitude) in openmeteo.POINTS.items():
        body = openmeteo.get(url, {
            'latitude': latitude, 'longitude': longitude, 'wind_speed_unit': 'kn', 'timezone': 'UTC', 'forecast_days': DAYS, **params,
        })
        frames.append(point_rows(body['hourly'], name, run, summarise))
    return pd.concat(frames, ignore_index=True)


SOURCES: dict[str, tuple[Callable[[], datetime], Callable[[datetime], pd.DataFrame]]] = {
    'ecmwf': (lambda: latest_run('https://api.open-meteo.com/data/ecmwf_ifs025/static/meta.json'), ecmwf),
    'ecmwf_ensemble': (lambda: latest_run('https://api.open-meteo.com/data/ecmwf_ifs025_ensemble/static/meta.json'), ecmwf_ensemble),
    'waves': (lambda: latest_run('https://marine-api.open-meteo.com/data/meteofrance_wave/static/meta.json'), waves),
}


if __name__ == '__main__':
    main(Path(sys.argv[1]))
