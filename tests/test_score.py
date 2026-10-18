import numpy as np
import pandas as pd
import pytest

from ferry import score

NOW = pd.Timestamp('2026-10-20T12:00:00Z')
EARLY = '2026-10-20T07:00:00.000Z'
LATE = '2026-10-20T18:00:00.000Z'


def prediction(observed_at: str, departs: str, days_ahead: int, chance: str) -> dict:
    return {'observed_at': observed_at, 'origin': 'Troon', 'destination': 'Brodick', 'departs': departs,
            'days_ahead': str(days_ahead), 'status': 'SCHEDULED', 'gust_knots': '30', 'chance_of_sailing': chance, 'model_sha256': 'abc'}


def sailing(observed_at: str, departs: str, status: str) -> dict:
    return {'observed_at': observed_at, 'sailing_date': departs[:10], 'route_code': '041', 'origin': 'Troon', 'destination': 'Brodick',
            'departs': departs, 'arrives': '', 'rescheduled_departs': '', 'status': status}


@pytest.mark.parametrize('predictions, sailings, expected', [
    pytest.param(
        [prediction('2026-10-19T08:00:00+00:00', EARLY, 1, '0.9'), prediction('2026-10-19T20:00:00+00:00', EARLY, 1, '0.6')],
        [sailing('2026-10-18T08:00:00+00:00', EARLY, 'SCHEDULED')],
        [(1, 0.6, False)],
        id='latest prediction at each days ahead',
    ),
    pytest.param(
        [prediction('2026-10-20T06:00:00+00:00', EARLY, 0, '0.9'), prediction('2026-10-20T08:00:00+00:00', EARLY, 0, '0.2')],
        [sailing('2026-10-18T08:00:00+00:00', EARLY, 'SCHEDULED')],
        [(0, 0.9, False)],
        id='predictions after departure are ignored',
    ),
    pytest.param(
        [prediction('2026-10-19T08:00:00+00:00', EARLY, 1, '0.4'), prediction('2026-10-20T05:00:00+00:00', EARLY, 0, '')],
        [sailing('2026-10-18T08:00:00+00:00', EARLY, 'SCHEDULED'), sailing('2026-10-20T04:00:00+00:00', EARLY, 'CANCELLED')],
        [(1, 0.4, True)],
        id='cancelled by its latest status, with no prediction once CalMac cancelled',
    ),
    pytest.param(
        [prediction('2026-10-19T08:00:00+00:00', EARLY, 1, '0.4')],
        [sailing('2026-10-19T09:00:00+00:00', EARLY, 'CANCELLED'), sailing('2026-10-19T10:00:00+00:00', EARLY, 'SCHEDULED')],
        [(1, 0.4, False)],
        id='reinstated sailing is not cancelled',
    ),
    pytest.param(
        [prediction('2026-10-19T08:00:00+00:00', LATE, 1, '0.9')],
        [sailing('2026-10-18T08:00:00+00:00', LATE, 'SCHEDULED')],
        [],
        id='sailing not yet departed is not scored',
    ),
])
def test_scored(predictions, sailings, expected):
    table = score.scored(pd.DataFrame(predictions), pd.DataFrame(sailings), NOW)

    assert list(table[['days_ahead', 'chance_of_sailing', 'cancelled']].itertuples(index=False, name=None)) == expected


def test_by_lead():
    table = pd.DataFrame({
        'days_ahead': [0, 0, 0, 1],
        'chance_of_sailing': [0.9, 0.8, 0.3, 0.9],
        'cancelled': [False, False, True, False],
    })

    lead = score.by_lead(table)

    assert lead.to_dict('records') == [
        {'days_ahead': 0, 'sailings': 3, 'cancelled': 1, 'auc': 1.0, 'brier': 0.0467, 'predicted_cancel_rate': 0.333, 'actual_cancel_rate': 0.333},
        {'days_ahead': 1, 'sailings': 1, 'cancelled': 0, 'auc': pytest.approx(np.nan, nan_ok=True), 'brier': 0.01, 'predicted_cancel_rate': 0.1, 'actual_cancel_rate': 0.0},
    ]


def test_by_band():
    table = pd.DataFrame({
        'chance_of_sailing': [1.0, 0.95, 0.9, 0.55],
        'cancelled': [False, False, True, False],
    })

    assert score.by_band(table).to_dict('records') == [
        {'chance_of_sailing': '50–60%', 'predictions': 1, 'predicted_chance': 0.55, 'sailed': 1.0},
        {'chance_of_sailing': '90–100%', 'predictions': 3, 'predicted_chance': 0.95, 'sailed': pytest.approx(0.667)},
    ]
