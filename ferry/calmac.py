from dataclasses import dataclass
from datetime import date

import requests

URL = 'https://apim.calmac.co.uk/graphql'
HEADERS = {'User-Agent': 'ferry-predictor (+https://github.com/SamKelsey/ferry-predictor)'}

SAILINGS_QUERY = """
query ($origin: String, $destination: String, $start: Date, $end: Date) {
  portPairSailings(
    where: {and: [
      {originPort: {name: {eq: $origin}}}
      {destinationPort: {name: {eq: $destination}}}
      {sailingDate: {gte: $start}}
      {sailingDate: {lt: $end}}
    ]}
    order: {departureDateTime: ASC}
  ) {
    sailingDate
    route { routeCode }
    departureDateTime
    arrivalDateTime
    rescheduledDepartureDateTime
    status
  }
}
"""

ROUTE_QUERY = """
query ($code: String) {
  routes(where: {routeCode: {eq: $code}}) {
    routeStatuses {
      id
      title
      status
      subStatus
      disruptionReason
      startDateTime
      endDateTime
      updatedAtDateTime
      detail
    }
    vessels { name }
  }
}
"""


@dataclass(frozen=True)
class Sailing:
    sailing_date: str
    route_code: str
    origin: str
    destination: str
    departs: str
    arrives: str
    rescheduled_departs: str | None
    status: str


@dataclass(frozen=True)
class Notice:
    route_code: str
    id: str
    title: str
    status: str
    sub_status: str
    disruption_reason: str | None
    starts: str
    ends: str
    updated_at: str
    detail: str


@dataclass(frozen=True)
class Route:
    notices: list[Notice]
    vessels: list[str]


def sailings(origin: str, destination: str, start: date, end: date) -> list[Sailing]:
    """Scheduled sailings between two ports, from `start` up to but not including `end`."""
    data = _query(SAILINGS_QUERY, {'origin': origin, 'destination': destination, 'start': start.isoformat(), 'end': end.isoformat()})
    return [
        Sailing(
            sailing_date=s['sailingDate'],
            route_code=s['route']['routeCode'],
            origin=origin,
            destination=destination,
            departs=s['departureDateTime'],
            arrives=s['arrivalDateTime'],
            rescheduled_departs=s['rescheduledDepartureDateTime'],
            status=s['status'],
        )
        for s in data['portPairSailings']
    ]


def route(code: str) -> Route:
    """The route's current notices and the vessels assigned to it."""
    [r] = _query(ROUTE_QUERY, {'code': code})['routes']
    return Route(
        notices=[
            Notice(
                route_code=code,
                id=n['id'],
                title=n['title'],
                status=n['status'],
                sub_status=n['subStatus'],
                disruption_reason=n['disruptionReason'],
                starts=n['startDateTime'],
                ends=n['endDateTime'],
                updated_at=n['updatedAtDateTime'],
                detail=n['detail'],
            )
            for n in r['routeStatuses']
        ],
        vessels=[v['name'] for v in r['vessels']],
    )


def _query(text: str, variables: dict[str, str]) -> dict:
    response = requests.post(URL, json={'query': text, 'variables': variables}, headers=HEADERS, timeout=60)
    response.raise_for_status()
    body = response.json()
    if body.get('errors'):
        raise RuntimeError(body['errors'])
    return body['data']
