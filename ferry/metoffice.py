import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import requests

# The Met Office's current warnings for Strathclyde, which covers Ardrossan, Troon and Arran.
URL = 'https://www.metoffice.gov.uk/public/data/PWSCache/WarningsRSS/Region/st'
TITLE = re.compile(r'^(\w+) warning of (.+?) affecting ')
DESCRIPTION = re.compile(r': (.+) valid from (\d{4}) \w{3} (\d{1,2} \w{3}) to (\d{4}) \w{3} (\d{1,2} \w{3})$')
UK = ZoneInfo('Europe/London')


@dataclass(frozen=True)
class WeatherWarning:
    id: str
    level: str | None
    hazard: str | None
    areas: str | None
    starts: str | None
    ends: str | None
    description: str


def warnings() -> list[WeatherWarning]:
    """The Met Office's weather warnings in force or coming up for Strathclyde."""
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    return parse(response.text)


def parse(feed: str) -> list[WeatherWarning]:
    """
    Warnings from the RSS feed. The feed gives validity as UK local times without a year, such as "valid from 0300 Tue 27 Oct";
    the year comes from the date in each warning's link. Parts it can't read are left empty rather than lost.
    """
    found = []
    for item in ET.fromstring(feed).iter('item'):
        title, description = item.findtext('title', ''), item.findtext('description', '')
        query = parse_qs(urlparse(item.findtext('link', '')).fragment.removeprefix('?'))
        level, hazard = (m[1], m[2]) if (m := TITLE.match(title)) else (None, None)
        areas = starts = ends = None
        if (m := DESCRIPTION.search(description)) and 'date' in query:
            year = int(query['date'][0][:4])
            areas, starts_at = m[1], _local(m[2], m[3], year)
            ends_at = _local(m[4], m[5], year)
            if ends_at < starts_at:
                ends_at = _local(m[4], m[5], year + 1)
            starts, ends = _utc(starts_at), _utc(ends_at)
        found.append(WeatherWarning(
            id=query['id'][0] if 'id' in query else title, level=level, hazard=hazard, areas=areas, starts=starts, ends=ends, description=description,
        ))
    return found


def _local(hhmm: str, day_month: str, year: int) -> datetime:
    return datetime.strptime(f'{day_month} {year} {hhmm}', '%d %b %Y %H%M').replace(tzinfo=UK)


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
