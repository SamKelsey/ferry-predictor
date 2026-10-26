from datetime import date

import pytest

from ferry import poll

TODAY, END = date(2026, 10, 26), date(2026, 11, 3)


def sailing(departs: str, status: str = 'SCHEDULED') -> dict:
    return {'sailing_date': departs[:10], 'route_code': '301', 'origin': 'Troon', 'destination': 'Brodick',
            'departs': departs, 'arrives': '', 'rescheduled_departs': '', 'status': status}


def logged(observed_at: str, row: dict) -> dict:
    return {'observed_at': observed_at, **row}


@pytest.mark.parametrize('history, observed, expected', [
    pytest.param(
        [logged('t0', sailing('2026-10-26T12:05:00.000Z'))],
        [],
        [sailing('2026-10-26T12:05:00.000Z', 'REMOVED')],
        id='listed sailing that disappears is removed',
    ),
    pytest.param(
        [logged('t0', sailing('2026-10-26T12:05:00.000Z'))],
        [sailing('2026-10-26T12:05:00.000Z')],
        [],
        id='sailing still listed is not removed',
    ),
    pytest.param(
        [logged('t0', sailing('2026-10-26T12:05:00.000Z')), logged('t1', sailing('2026-10-26T12:05:00.000Z', 'REMOVED'))],
        [],
        [],
        id='removed sailing is not removed again',
    ),
    pytest.param(
        [logged('t0', sailing('2026-10-25T12:05:00.000Z'))],
        [],
        [],
        id='sailing before today is no longer watched',
    ),
    pytest.param(
        [logged('t0', sailing('2026-11-03T12:05:00.000Z'))],
        [],
        [],
        id='sailing beyond the watched days is not removed',
    ),
])
def test_removed(history, observed, expected):
    assert poll.removed(history, observed, TODAY, END) == expected
