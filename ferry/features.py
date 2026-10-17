import numpy as np
import pandas as pd

from ferry.openmeteo import POINTS


def local(hourly: pd.DataFrame) -> pd.DataFrame:
    """Hourly UTC weather moved onto a UK local-time index, with one row for every hour."""
    h = hourly.copy()
    h.index = h.index.tz_localize('UTC').tz_convert('Europe/London').tz_localize(None)
    return h.groupby(level=0).first().asfreq('h')


def timetable(sailings: pd.DataFrame) -> pd.DataFrame:
    """Sailings with their local date and their place among their route's sailings that day."""
    s = sailings.sort_values(['route', 'departs']).reset_index(drop=True)
    s['date'] = s.departs.dt.normalize()
    day = s.groupby(['route', 'date'])
    s['n_day'] = day.departs.transform('size')
    s['i_day'] = day.cumcount()
    return s


def build(hourly: pd.DataFrame, sailings: pd.DataFrame) -> pd.DataFrame:
    """The model's features for each sailing in a `timetable`, from `local` hourly weather."""
    return pd.concat([weather(hourly, sailings), schedule(sailings)], axis=1)


def weather(hourly: pd.DataFrame, sailings: pd.DataFrame) -> pd.DataFrame:
    at = sailings.departs.dt.floor('h')
    columns: dict[str, np.ndarray] = {}
    for point in POINTS:
        gust = hourly[f'{point}_wind_gusts_10m']
        wind = hourly[f'{point}_wind_speed_10m']
        direction = np.deg2rad(hourly[f'{point}_wind_direction_10m'])
        daytime = gust[(gust.index.hour >= 6) & (gust.index.hour < 22)]
        columns[f'{point}_gust'] = gust.reindex(at).values
        columns[f'{point}_wind'] = wind.reindex(at).values
        columns[f'{point}_gust_window'] = gust.rolling(7, center=True, min_periods=1).max().reindex(at).values
        columns[f'{point}_wind_window'] = wind.rolling(7, center=True, min_periods=1).max().reindex(at).values
        columns[f'{point}_gust_east'] = (gust * np.sin(direction)).reindex(at).values
        columns[f'{point}_gust_north'] = (gust * np.cos(direction)).reindex(at).values
        columns[f'{point}_gust_day'] = daytime.groupby(daytime.index.normalize()).max().reindex(sailings.date).values
        columns[f'{point}_gust_overnight'] = gust.rolling(12, min_periods=1).max().reindex(sailings.date + pd.Timedelta(hours=6)).values
    pressure = hourly['troon_pressure_msl']
    columns['pressure'] = pressure.reindex(at).values
    columns['pressure_change'] = (pressure - pressure.shift(6)).reindex(at).values
    w = pd.DataFrame(columns, index=sailings.index)
    troon = sailings.route.eq('TRO').values
    w['port_gust'] = np.where(troon, w.troon_gust, w.ardrossan_gust)
    w['port_gust_window'] = np.where(troon, w.troon_gust_window, w.ardrossan_gust_window)
    return w


def schedule(sailings: pd.DataFrame) -> pd.DataFrame:
    day_of_year = sailings.departs.dt.dayofyear
    return pd.DataFrame({
        'troon': sailings.route.eq('TRO').astype(int),
        'from_brodick': sailings.from_brodick,
        'hour': sailings.departs.dt.hour + sailings.departs.dt.minute / 60,
        'first_of_day': (sailings.i_day == 0).astype(int),
        'last_of_day': (sailings.i_day == sailings.n_day - 1).astype(int),
        'sailings_that_day': sailings.n_day,
        'position_in_day': sailings.i_day,
        'passage_mins': sailings.passage_mins,
        'season_sin': np.sin(2 * np.pi * day_of_year / 365.25),
        'season_cos': np.cos(2 * np.pi * day_of_year / 365.25),
        'weekday': sailings.departs.dt.dayofweek,
    }, index=sailings.index)
