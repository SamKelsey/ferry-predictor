from dataclasses import dataclass

import pytest

from ferry import logbook

KEY = ('id',)


@pytest.mark.parametrize('logged, observed, expected', [
    pytest.param(
        [],
        [{'id': '1', 'status': 'SCHEDULED'}],
        [{'id': '1', 'status': 'SCHEDULED'}],
        id='first sighting is a change',
    ),
    pytest.param(
        [{'observed_at': 't0', 'id': '1', 'status': 'SCHEDULED'}],
        [{'id': '1', 'status': 'SCHEDULED'}],
        [],
        id='unchanged row is not a change',
    ),
    pytest.param(
        [{'observed_at': 't0', 'id': '1', 'status': 'SCHEDULED'}],
        [{'id': '1', 'status': 'CANCELLED'}],
        [{'id': '1', 'status': 'CANCELLED'}],
        id='changed value is a change',
    ),
    pytest.param(
        [{'observed_at': 't0', 'id': '1', 'status': 'SCHEDULED'}, {'observed_at': 't1', 'id': '1', 'status': 'CANCELLED'}],
        [{'id': '1', 'status': 'CANCELLED'}],
        [],
        id='compared against the latest logged row',
    ),
    pytest.param(
        [{'observed_at': 't0', 'id': '1', 'status': 'SCHEDULED'}],
        [{'id': '1', 'status': 'SCHEDULED'}, {'id': '2', 'status': 'SCHEDULED'}],
        [{'id': '2', 'status': 'SCHEDULED'}],
        id='only the changed rows of several',
    ),
])
def test_changes(logged, observed, expected):
    assert logbook.changes(logged, observed, KEY) == expected


@dataclass
class Item:
    id: str
    rescheduled: str | None


def test_record_appends_only_changes(tmp_path):
    path = tmp_path / 'log.csv'
    polls = [
        ('t0', [Item('1', None)], 1),
        ('t1', [Item('1', None)], 0),
        ('t2', [Item('1', '10:30')], 1),
    ]
    for observed_at, items, expected in polls:
        assert logbook.record(path, [logbook.row(i) for i in items], KEY, observed_at) == expected

    assert logbook.read(path) == [
        {'observed_at': 't0', 'id': '1', 'rescheduled': ''},
        {'observed_at': 't2', 'id': '1', 'rescheduled': '10:30'},
    ]
