import pandas as pd

from ferry import foi

HEADER = ('Year,Month,Scheduled Departure Date,Scheduled Departure Time,Scheduled Arrival Time,Actual Departure Date,'
          'Actual Departure Time,Actual Arrival Time,Scheduled Passage Minutes,Actual Passage Minutes,Route,Scheduled Leg,Operated Leg,'
          'Ship Name,Contractual Outcome,Cancelled (Weather),Cancelled (Technical),Cancelled (Other),Late (Weather),Late (Tech),'
          'Late (Other),Diverted Sailings,Returned to Port Sailings')
ROWS = [
    '2026,October,18/10/2026,09:45 AM,10:40 AM,18/10/2026,09:45 AM,10:40 AM,55,55,Ardrossan - Brodick,Ardrossan-Brodick,Ardrossan-Brodick,MV Caledonian Isles,On Time,0,0,0,0,0,0,0,0',
    '2026,October,18/10/2026,10:15 PM,11:35 PM,,,,80,,Ardrossan - Brodick,Brodick-Troon,Brodick-Troon,MV Alfred,Cancelled,1,0,0,0,0,0,0,0',
    '2026,October,18/10/2026,01:00 PM,02:00 PM,18/10/2026,01:00 PM,02:00 PM,60,60,Ardrossan - Brodick,Ardrossan-Brodick,Ardrossan-Brodick,MV Caledonian Isles,Additional,0,0,0,0,0,0,0,0',
    '2026,October,18/10/2026,02:00 PM,03:00 PM,18/10/2026,02:00 PM,03:00 PM,60,60,Ardrossan - Brodick,Gourock (Dunoon)-Brodick,Gourock (Dunoon)-Brodick,MV Isle of Arran,On Time,0,0,0,0,0,0,0,0',
]


def test_sailings_keeps_scheduled_arran_sailings(tmp_path):
    path = tmp_path / 'foi.csv'
    path.write_text('﻿' + '\n'.join([HEADER, *ROWS]))

    s = foi.sailings(path)

    assert s.to_dict('records') == [
        {'departs': pd.Timestamp('2026-10-18 09:45'), 'route': 'ARD', 'from_brodick': 0, 'passage_mins': 55, 'cancelled': 0},
        {'departs': pd.Timestamp('2026-10-18 22:15'), 'route': 'TRO', 'from_brodick': 1, 'passage_mins': 80, 'cancelled': 1},
    ]
