from pathlib import Path

import pandas as pd

ROUTES = {'Ardrossan-Brodick': 'ARD', 'Brodick-Ardrossan': 'ARD', 'Troon-Brodick': 'TRO', 'Brodick-Troon': 'TRO'}
SCHEDULED_OUTCOMES = ['On Time', 'Cancelled', 'Level 1 Lateness', 'Level 2 Lateness']


def sailings(path: Path) -> pd.DataFrame:
    """Scheduled Arran sailings from CalMac's FOI 4377 release, with whether each was cancelled."""
    raw = pd.read_csv(path, encoding='utf-8-sig', dtype=str)
    raw = raw[raw['Contractual Outcome'].isin(SCHEDULED_OUTCOMES) & raw['Leg Description'].isin(ROUTES)]
    return pd.DataFrame({
        'departs': pd.to_datetime(raw['Sched Dept Date'] + ' ' + raw['Sched Dept Time'], format='%d/%m/%Y %H:%M'),
        'route': raw['Leg Description'].map(ROUTES),
        'from_brodick': raw['Leg Description'].str.startswith('Brodick').astype(int),
        'passage_mins': pd.to_numeric(raw['Scheduled Passage Mins']),
        'cancelled': raw['Contractual Outcome'].eq('Cancelled').astype(int),
    }).reset_index(drop=True)
