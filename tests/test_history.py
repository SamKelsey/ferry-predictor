import numpy as np
import pandas as pd
import pytest

from ferry import history


def outcomes(*rows: tuple[str, str, int]) -> pd.DataFrame:
    return pd.DataFrame({'route': [r for r, _, _ in rows], 'date': pd.to_datetime([d for _, d, _ in rows]), 'cancelled': [c for _, _, c in rows]})


def sailings(*rows: tuple[str, str]) -> pd.DataFrame:
    return pd.DataFrame({'route': [r for r, _ in rows], 'date': pd.to_datetime([d for _, d in rows])})


def test_cancellations_count_back_from_days_before():
    past = outcomes(('ARD', '2026-10-20', 1), ('ARD', '2026-10-20', 1), ('ARD', '2026-10-21', 0), ('ARD', '2026-10-24', 1), ('TRO', '2026-10-24', 1))

    counts = history.cancellations(sailings(('ARD', '2026-10-25'), ('ARD', '2026-10-25')), past, np.array([1, 4]))

    assert counts.to_dict('records') == [
        {'route_cancelled_1d': 1, 'route_cancelled_7d': 3, 'route_cancelled_28d': 3},
        {'route_cancelled_1d': 0, 'route_cancelled_7d': 2, 'route_cancelled_28d': 2},
    ]


def test_cancellations_beyond_the_outcomes_read_as_quiet():
    counts = history.cancellations(sailings(('ARD', '2026-11-30'), ('TRO', '2026-10-25')), outcomes(('ARD', '2026-10-20', 1)), 1)

    assert counts.to_numpy().tolist() == [[0, 0, 0], [0, 0, 0]]


def logged_sailing(observed_at: str, departs: str, status: str, route_code: str = '003') -> dict:
    return {'observed_at': observed_at, 'sailing_date': departs[:10], 'route_code': route_code, 'origin': 'Ardrossan', 'destination': 'Brodick',
            'departs': departs, 'arrives': '', 'rescheduled_departs': '', 'status': status}


def logged_notice(sub_status: str, starts: str, ends: str, title: str = '') -> dict:
    return {'observed_at': starts, 'route_code': '003', 'id': f'n-{starts}', 'title': title, 'status': 'SAILING', 'sub_status': sub_status,
            'disruption_reason': 'Weather', 'starts': starts, 'ends': ends, 'updated_at': starts, 'detail': ''}


@pytest.mark.parametrize('sailings_log, notices_log, expected', [
    pytest.param(
        [logged_sailing('t0', '2026-10-26T07:00:00.000Z', 'SCHEDULED'), logged_sailing('t1', '2026-10-26T07:00:00.000Z', 'REMOVED'),
         logged_sailing('t0', '2026-10-26T09:45:00.000Z', 'SCHEDULED')],
        [],
        [1, 0],
        id='removed sailing is cancelled, listed one sailed',
    ),
    pytest.param(
        [logged_sailing('t0', '2026-10-23T07:00:00.000Z', 'SCHEDULED'), logged_sailing('t0', '2026-10-23T09:45:00.000Z', 'SCHEDULED')],
        [logged_notice('ALL_SAILINGS_CANCELLED', '2026-10-22T15:00:00.000Z', '2026-10-24T00:00:00.000Z')],
        [1, 1],
        id='day cancelled outright by a notice',
    ),
    pytest.param(
        [logged_sailing('t0', '2026-10-22T07:00:00.000Z', 'SCHEDULED'), logged_sailing('t0', '2026-10-23T07:00:00.000Z', 'SCHEDULED')],
        [logged_notice('ALL_SAILINGS_CANCELLED', '2026-10-22T15:10:00.000Z', '2026-10-24T00:00:00.000Z', title='Friday 23 October ')],
        [0, 1],
        id='a dated notice posted the afternoon before covers only its own day',
    ),
    pytest.param(
        [logged_sailing('t0', '2026-10-26T07:00:00.000Z', 'SCHEDULED'), logged_sailing('t1', '2026-10-26T07:00:00.000Z', 'REMOVED'),
         logged_sailing('t0', '2026-10-26T09:45:00.000Z', 'SCHEDULED')],
        [logged_notice('ALL_SAILINGS_CANCELLED', '2026-10-25T10:00:00.000Z', '2026-10-27T00:00:00.000Z')],
        [1, 0],
        id='logged removals beat a whole-day notice',
    ),
    pytest.param(
        [logged_sailing('t0', '2026-10-27T07:00:00.000Z', 'REMOVED')],
        [],
        [],
        id='sailings on or after the cut-off are left out',
    ),
])
def test_observed(sailings_log, notices_log, expected):
    assert history.observed(sailings_log, notices_log, '2026-10-27').cancelled.tolist() == expected
