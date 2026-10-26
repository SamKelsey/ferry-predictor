from ferry import metoffice


def feed(*items: tuple[str, str, str]) -> str:
    entries = ''.join(
        f'<item><title>{title}</title><link>https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-warnings#?date={day}&amp;id={id}&amp;referrer=rss</link>'
        f'<description>{description}</description></item>'
        for title, description, (day, id) in items
    )
    return f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Met Office warnings for Strathclyde</title>{entries}</channel></rss>'


def test_parse_reads_level_hazard_areas_and_validity_in_utc():
    xml = feed((
        'Yellow warning of wind affecting Strathclyde',
        'Yellow warning of wind affecting Strathclyde: North Ayrshire, South Ayrshire valid from 0300 Tue 27 Oct to 2100 Tue 27 Oct',
        ('2026-10-27', 'abc-123'),
    ))

    assert metoffice.parse(xml) == [metoffice.WeatherWarning(
        id='abc-123', level='Yellow', hazard='wind', areas='North Ayrshire, South Ayrshire',
        starts='2026-10-27T03:00:00Z', ends='2026-10-27T21:00:00Z',
        description='Yellow warning of wind affecting Strathclyde: North Ayrshire, South Ayrshire valid from 0300 Tue 27 Oct to 2100 Tue 27 Oct',
    )]


def test_parse_handles_summer_time_and_the_new_year():
    xml = feed(
        ('Amber warning of wind affecting Strathclyde', 'Amber warning of wind affecting Strathclyde: Inverclyde valid from 1800 Thu 31 Dec to 0600 Fri 1 Jan',
         ('2026-12-31', 'new-year')),
        ('Yellow warning of rain affecting Strathclyde', 'Yellow warning of rain affecting Strathclyde: Glasgow valid from 1200 Sat 4 Jul to 1800 Sat 4 Jul',
         ('2026-07-04', 'summer')),
    )

    starts_ends = [(w.id, w.starts, w.ends) for w in metoffice.parse(xml)]

    assert starts_ends == [
        ('new-year', '2026-12-31T18:00:00Z', '2027-01-01T06:00:00Z'),
        ('summer', '2026-07-04T11:00:00Z', '2026-07-04T17:00:00Z'),
    ]


def test_parse_keeps_a_warning_whose_wording_it_does_not_recognise():
    xml = feed(('Something new', 'A description in a new format', ('2026-10-27', 'odd')))

    assert metoffice.parse(xml) == [metoffice.WeatherWarning(
        id='odd', level=None, hazard=None, areas=None, starts=None, ends=None, description='A description in a new format',
    )]
