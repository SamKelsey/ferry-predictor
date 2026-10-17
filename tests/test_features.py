import numpy as np
import pandas as pd
import pytest

from ferry import features
from ferry.openmeteo import POINTS


def sailings(*departures: tuple[str, str]) -> pd.DataFrame:
    return features.timetable(pd.DataFrame({
        'route': [route for route, _ in departures],
        'departs': pd.to_datetime([departs for _, departs in departures]),
        'from_brodick': 0,
        'passage_mins': 55,
    }))


@pytest.mark.parametrize('departures, positions, counts', [
    pytest.param([('ARD', '2026-10-18 07:00')], [0], [1], id='single sailing'),
    pytest.param([('ARD', '2026-10-18 12:00'), ('ARD', '2026-10-18 07:00')], [0, 1], [2, 2], id='ordered by departure'),
    pytest.param([('ARD', '2026-10-18 07:00'), ('TRO', '2026-10-18 08:00')], [0, 0], [1, 1], id='routes counted apart'),
    pytest.param([('ARD', '2026-10-18 07:00'), ('ARD', '2026-10-19 07:00')], [0, 0], [1, 1], id='days counted apart'),
])
def test_timetable(departures, positions, counts):
    s = sailings(*departures)
    assert s.i_day.tolist() == positions
    assert s.n_day.tolist() == counts


def test_weather_around_departure():
    hours = pd.date_range('2026-10-17 18:00', '2026-10-18 23:00', freq='h')
    gust = pd.Series(10.0, index=hours)
    gust['2026-10-17 23:00'] = 40
    gust['2026-10-18 09:00'] = 30
    gust['2026-10-18 20:00'] = 35
    hourly = pd.DataFrame({'troon_pressure_msl': 1000.0}, index=hours)
    for point in POINTS:
        hourly[f'{point}_wind_gusts_10m'] = gust
        hourly[f'{point}_wind_speed_10m'] = gust / 2
        hourly[f'{point}_wind_direction_10m'] = 180.0

    w = features.weather(hourly, sailings(('TRO', '2026-10-18 12:00')))

    assert w.port_gust.item() == 10
    assert w.port_gust_window.item() == 30
    assert w.troon_gust_day.item() == 35
    assert w.troon_gust_overnight.item() == 40
    assert w.troon_gust_north.item() == pytest.approx(-10)


def test_local_fills_missing_hours():
    hourly = pd.DataFrame({'x': [1.0, 2.0]}, index=pd.to_datetime(['2026-10-17 10:00', '2026-10-17 12:00']))
    local = features.local(hourly)
    assert local.index.tolist() == list(pd.date_range('2026-10-17 11:00', '2026-10-17 13:00', freq='h'))
    assert np.isnan(local.x.iloc[1])
