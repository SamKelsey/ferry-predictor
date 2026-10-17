# data

Observations logged every 10 minutes by the [poll workflow](../../blob/main/.github/workflows/poll.yml). Each CSV is append-only: a row is added whenever something changes, stamped with `observed_at` (UTC).

- `sailings.csv` — each sailing's status and any rescheduled departure, keyed by route, origin, destination and scheduled departure.
- `notices.csv` — each route's service notices, including CalMac's disruption reason.
- `vessels.csv` — the vessels assigned to each route.
