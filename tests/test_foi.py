import pandas as pd

from ferry import foi

HEADER = ('Sched Dept Date,Sched Dept Time,Sched Arr Time,Act Dept Date,Act Dept Time,Act Arr Time,Scheduled Passage Mins,'
          'Actual Passage Mins,Leg Description,Act Leg Description,Contractual Outcome,Cancelled Due Weather,Cancelled Due Tech,'
          'Cancelled Due Other,Late (Weather),Late (Tech),Late (Other),Diverted,Returned to Port')
ROWS = [
    '18/10/2026,09:45,10:40,18/10/2026,09:45,10:40,55,55,Ardrossan-Brodick,Ardrossan-Brodick,On Time,0,0,0,0,0,0,0,0',
    '18/10/2026,10:15,11:35,,,,80,,Brodick-Troon,,Cancelled,1,0,0,0,0,0,0,0',
    '18/10/2026,13:00,14:00,18/10/2026,13:00,14:00,60,60,Ardrossan-Brodick,Ardrossan-Brodick,Additional,0,0,0,0,0,0,0,0',
    '18/10/2026,14:00,15:00,18/10/2026,14:00,15:00,60,60,Gourock-Brodick,Gourock-Brodick,On Time,0,0,0,0,0,0,0,0',
    'Total,,,,,,,,,,,"4,217","2,054","1,017",662,567,"1,588",420,22',
]


def test_sailings_keeps_scheduled_arran_sailings(tmp_path):
    path = tmp_path / 'foi.csv'
    path.write_text('﻿' + '\n'.join([HEADER, *ROWS]))

    s = foi.sailings(path)

    assert s.to_dict('records') == [
        {'departs': pd.Timestamp('2026-10-18 09:45'), 'route': 'ARD', 'from_brodick': 0, 'passage_mins': 55, 'cancelled': 0},
        {'departs': pd.Timestamp('2026-10-18 10:15'), 'route': 'TRO', 'from_brodick': 1, 'passage_mins': 80, 'cancelled': 1},
    ]
