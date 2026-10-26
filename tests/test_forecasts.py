from datetime import datetime, timezone

import pandas as pd
import pytest

from ferry import forecasts

RUN = datetime(2026, 10, 26, 0, tzinfo=timezone.utc)


def test_point_rows_keep_every_third_hour_from_the_run():
    hourly = {'time': ['2026-10-25T21:00', '2026-10-26T00:00', '2026-10-26T01:00', '2026-10-26T03:00'], 'wave_height': [1.0, 1.5, 1.6, 2.0]}

    rows = forecasts.point_rows(hourly, 'troon', RUN, forecasts.as_is)

    assert rows.to_dict('records') == [
        {'run': '2026-10-26T00:00Z', 'point': 'troon', 'time': '2026-10-26T00:00Z', 'lead_hours': 0, 'wave_height': 1.5},
        {'run': '2026-10-26T00:00Z', 'point': 'troon', 'time': '2026-10-26T03:00Z', 'lead_hours': 3, 'wave_height': 2.0},
    ]


def test_ensemble_summary_describes_the_spread_of_members():
    hourly = pd.DataFrame({
        'wind_gusts_10m': [20.0], 'wind_gusts_10m_member01': [32.0], 'wind_gusts_10m_member02': [36.0], 'wind_gusts_10m_member03': [44.0],
        'wind_speed_10m': [10.0], 'wind_speed_10m_member01': [16.0], 'wind_speed_10m_member02': [18.0], 'wind_speed_10m_member03': [22.0],
        'wind_direction_10m': [180.0], 'wind_direction_10m_member01': [180.0], 'wind_direction_10m_member02': [270.0], 'wind_direction_10m_member03': [270.0],
    })

    s = forecasts.ensemble_summary(hourly).iloc[0]

    assert s.members == 4
    assert s.gust_p50 == 34
    assert s.gust_max == 44
    assert (s.gust_over_30, s.gust_over_35, s.gust_over_40) == (0.75, 0.5, 0.25)
    assert s.wind_p50 == 17
    assert s.direction == pytest.approx(225)
    assert s.direction_agreement == pytest.approx(0.707, abs=1e-3)


def test_main_saves_each_run_once(tmp_path, monkeypatch):
    calls = []

    def fetch(run):
        calls.append(run)
        return pd.DataFrame({'run': ['r'], 'value': [1]})

    monkeypatch.setattr(forecasts, 'SOURCES', {'waves': (lambda: RUN, fetch)})

    forecasts.main(tmp_path)
    forecasts.main(tmp_path)

    assert calls == [RUN]
    assert (tmp_path / 'forecasts' / 'waves' / '2026-10-26T00.csv').read_text() == 'run,value\nr,1\n'


def test_main_skips_short_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(forecasts, 'SOURCES', {'ecmwf': (lambda: RUN.replace(hour=6), lambda run: pytest.fail('fetched a short run'))})

    forecasts.main(tmp_path)

    assert not (tmp_path / 'forecasts').exists()
