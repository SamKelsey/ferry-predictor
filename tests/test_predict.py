from datetime import date

import numpy as np
import pandas as pd

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
        '301': [notice('NONE')],
    }

    rows = predict.routes(notices, '2026-10-19T07:00:00+00:00')

    assert [(r['route'], r['status'], [n['status'] for n in r['notices']]) for r in rows] == [
        ('ARD', 'DISRUPTIONS', ['DISRUPTIONS', 'BE_AWARE']),
        ('TRO', 'NORMAL', []),
    ]
    assert rows[0]['notices'][0] == {
        'title': 'Monday 19 October', 'status': 'DISRUPTIONS', 'reason': 'Emergency',
        'updated_at': '2026-10-19T06:00:00.000Z', 'detail': 'The following sailings are **cancelled**',
    }
