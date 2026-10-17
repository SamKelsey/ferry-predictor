from datetime import date

import pytest

from ferry import calmac


class Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def sailing_json(status, rescheduled):
    return {
        'sailingDate': '2026-10-18',
        'route': {'routeCode': '301'},
        'departureDateTime': '2026-10-18T09:15:00.000Z',
        'arrivalDateTime': '2026-10-18T10:35:00.000Z',
        'rescheduledDepartureDateTime': rescheduled,
        'status': status,
    }


@pytest.mark.parametrize('status, rescheduled', [
    pytest.param('SCHEDULED', None, id='on schedule'),
    pytest.param('DELAYED', '2026-10-18T10:00:00.000Z', id='delayed'),
    pytest.param('CANCELLED', None, id='cancelled'),
])
def test_sailings(monkeypatch, status, rescheduled):
    body = {'data': {'portPairSailings': [sailing_json(status, rescheduled)]}}
    monkeypatch.setattr(calmac.requests, 'post', lambda *a, **k: Response(body))

    assert calmac.sailings('Troon', 'Brodick', date(2026, 10, 18), date(2026, 10, 19)) == [
        calmac.Sailing(
            sailing_date='2026-10-18',
            route_code='301',
            origin='Troon',
            destination='Brodick',
            departs='2026-10-18T09:15:00.000Z',
            arrives='2026-10-18T10:35:00.000Z',
            rescheduled_departs=rescheduled,
            status=status,
        )
    ]


def test_query_errors_are_raised(monkeypatch):
    monkeypatch.setattr(calmac.requests, 'post', lambda *a, **k: Response({'errors': [{'message': 'bad query'}]}))

    with pytest.raises(RuntimeError, match='bad query'):
        calmac.route('301')
