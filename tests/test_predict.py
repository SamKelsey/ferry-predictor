from datetime import date

import numpy as np
import pandas as pd
import pytest

from ferry import calmac, predict


def test_entries_defers_to_calmac_cancellations_and_sorts_by_departure():
    sailings = pd.DataFrame({
        'origin': ['Troon', 'Brodick'],
        'destination': ['Brodick', 'Troon'],
        'departs_at': ['2026-10-18T13:10:00.000Z', '2026-10-18T09:15:00.000Z'],
        'arrives': ['2026-10-18T14:30:00.000Z', '2026-10-18T10:35:00.000Z'],
        'rescheduled_departs': [None, '2026-10-18T09:45:00.000Z'],
        'status': ['CANCELLED', 'DELAYED'],
    })

    rows = predict.entries(sailings, pd.Series([41.6, np.nan]), np.array([0.9, 0.2]))

    assert rows == [
        {'origin': 'Brodick', 'destination': 'Troon', 'departs': '2026-10-18T09:15:00.000Z', 'arrives': '2026-10-18T10:35:00.000Z',
         'rescheduled_departs': '2026-10-18T09:45:00.000Z', 'status': 'DELAYED', 'gust_knots': None, 'chance_of_sailing': 0.8},
        {'origin': 'Troon', 'destination': 'Brodick', 'departs': '2026-10-18T13:10:00.000Z', 'arrives': '2026-10-18T14:30:00.000Z',
         'rescheduled_departs': None, 'status': 'CANCELLED', 'gust_knots': 42, 'chance_of_sailing': None},
    ]


def test_log_rows_counts_days_ahead_in_london_time():
    entries = [
        {'origin': 'Brodick', 'destination': 'Troon', 'departs': '2026-10-18T23:30:00.000Z', 'arrives': '2026-10-19T00:50:00.000Z',
         'rescheduled_departs': None, 'status': 'SCHEDULED', 'gust_knots': 31, 'chance_of_sailing': 0.82},
        {'origin': 'Troon', 'destination': 'Brodick', 'departs': '2026-10-18T13:10:00.000Z', 'arrives': '2026-10-18T14:30:00.000Z',
         'rescheduled_departs': None, 'status': 'CANCELLED', 'gust_knots': None, 'chance_of_sailing': None},
    ]

    rows = predict.log_rows(entries, date(2026, 10, 18), 'abc123')

    assert rows == [
        {'origin': 'Brodick', 'destination': 'Troon', 'departs': '2026-10-18T23:30:00.000Z', 'days_ahead': '1',
         'status': 'SCHEDULED', 'gust_knots': '31', 'chance_of_sailing': '0.82', 'model_sha256': 'abc123'},
        {'origin': 'Troon', 'destination': 'Brodick', 'departs': '2026-10-18T13:10:00.000Z', 'days_ahead': '0',
         'status': 'CANCELLED', 'gust_knots': '', 'chance_of_sailing': '', 'model_sha256': 'abc123'},
    ]


def notice(sub_status, updated_at='2026-10-19T06:00:00.000Z', status='SAILING', starts='2026-10-19T05:00:00.000Z', ends='2026-10-19T23:00:00.000Z'):
    return calmac.Notice(
        route_code='003', id=f'routestatus-{sub_status}-{updated_at}', title='Monday 19 October', status=status,
        sub_status=sub_status, disruption_reason='Emergency ', starts=starts, ends=ends, updated_at=updated_at,
        detail='The following sailings are **cancelled**',
    )


def test_routes_take_the_worst_live_sailing_notice():
    notices = {
        '003': [
            notice('BE_AWARE', updated_at='2026-10-19T06:30:00.000Z'),
            notice('DISRUPTIONS'),
            notice('NONE'),
            notice('BE_AWARE', status='SERVICE'),
            notice('ALL_SAILINGS_CANCELLED', ends='2026-10-19T06:00:00.000Z'),
        ],
        '301': [notice('NONE'), notice('BE_AWARE', starts='2026-10-19T19:45:00.000Z', ends='2026-10-21T00:00:00.000Z')],
    }

    rows = predict.routes(notices, '2026-10-19T07:00:00+00:00')

    assert [(r['route'], r['status'], [n['status'] for n in r['notices']]) for r in rows] == [
        ('ARD', 'DISRUPTIONS', ['DISRUPTIONS', 'BE_AWARE']),
        ('TRO', 'BE_AWARE', ['BE_AWARE']),
    ]
    assert rows[0]['notices'][0] == {
        'title': 'Monday 19 October', 'status': 'DISRUPTIONS', 'reason': 'Emergency',
        'starts': '2026-10-19T05:00:00.000Z', 'ends': '2026-10-19T23:00:00.000Z',
        'updated_at': '2026-10-19T06:00:00.000Z', 'detail': 'The following sailings are **cancelled**',
    }


def logged_sailing(route_code, origin, destination, departs, sailing_date='2026-10-27'):
    return {
        'observed_at': '2026-10-20T00:00:00+00:00', 'sailing_date': sailing_date, 'route_code': route_code, 'origin': origin,
        'destination': destination, 'departs': departs, 'arrives': departs.replace('T07', 'T08'), 'rescheduled_departs': '',
        'status': 'SCHEDULED',
    }


def test_dropped_brings_back_a_cancelled_days_sailings_as_cancelled():
    logged = [
        logged_sailing('003', 'Ardrossan', 'Brodick', '2026-10-27T07:00:00.000Z'),
        logged_sailing('003', 'Brodick', 'Ardrossan', '2026-10-27T07:20:00.000Z'),
        logged_sailing('003', 'Ardrossan', 'Brodick', '2026-10-28T07:00:00.000Z', sailing_date='2026-10-28'),
        logged_sailing('301', 'Troon', 'Brodick', '2026-10-27T07:15:00.000Z'),
    ]
    still_listed = calmac.Sailing('2026-10-27', '003', 'Brodick', 'Ardrossan', '2026-10-27T07:20:00.000Z',
                                  '2026-10-27T08:20:00.000Z', None, 'SCHEDULED')
    notices = {
        '003': [notice('ALL_SAILINGS_CANCELLED', starts='2026-10-26T19:45:00.000Z', ends='2026-10-28T00:00:00.000Z')],
        '301': [notice('DISRUPTIONS', starts='2026-10-26T19:45:00.000Z', ends='2026-10-28T00:00:00.000Z')],
    }

    found = predict.dropped(logged, [still_listed], notices, date(2026, 10, 26), date(2026, 11, 3))

    assert found == [calmac.Sailing('2026-10-27', '003', 'Ardrossan', 'Brodick', '2026-10-27T07:00:00.000Z',
                                    '2026-10-27T08:00:00.000Z', None, 'CANCELLED')]


def test_dropped_uses_the_latest_logged_timetable():
    old = logged_sailing('003', 'Ardrossan', 'Brodick', '2026-10-27T07:00:00.000Z')
    new = {**old, 'observed_at': '2026-10-22T00:00:00+00:00', 'arrives': '2026-10-27T08:05:00.000Z'}
    notices = {'003': [notice('ALL_SAILINGS_CANCELLED', starts='2026-10-26T19:45:00.000Z', ends='2026-10-28T00:00:00.000Z')]}

    [found] = predict.dropped([old, new], [], notices, date(2026, 10, 26), date(2026, 11, 3))

    assert found.arrives == '2026-10-27T08:05:00.000Z'


@pytest.mark.parametrize('starts, ends, day, expected', [
    pytest.param('2026-10-19T05:14:00.000Z', '2026-10-19T23:00:00.000Z', '2026-10-19', True, id='posted that morning'),
    pytest.param('2026-10-26T19:45:00.000Z', '2026-10-28T00:00:00.000Z', '2026-10-26', False, id='posted after the last sailing'),
    pytest.param('2026-10-26T19:45:00.000Z', '2026-10-28T00:00:00.000Z', '2026-10-27', True, id='the day it was posted for'),
    pytest.param('2026-10-26T19:45:00.000Z', '2026-10-28T00:00:00.000Z', '2026-10-28', False, id='ends at midnight'),
    pytest.param('2026-10-26T13:00:00.000Z', '2026-10-27T00:00:00.000Z', '2026-10-26', True, id='posted in the afternoon'),
])
def test_covers_only_counts_sailing_hours(starts, ends, day, expected):
    assert calmac.covers(notice('ALL_SAILINGS_CANCELLED', starts=starts, ends=ends), day) is expected
