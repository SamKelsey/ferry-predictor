import numpy as np
import pandas as pd

from ferry import predict


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
