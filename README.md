# data

Observations logged every 10 minutes by the [poll workflow](../../blob/main/.github/workflows/poll.yml), and predictions logged by the [publish workflow](../../blob/main/.github/workflows/site.yml) each time it rebuilds the site. Each CSV is append-only: a row is added whenever something changes, stamped with `observed_at` (UTC).

- `sailings.csv` — each sailing's status and any rescheduled departure, keyed by route, origin, destination and scheduled departure.
- `notices.csv` — each route's service notices, including CalMac's disruption reason.
- `vessels.csv` — the vessels assigned to each route.
- `predictions.csv` — each sailing's predicted chance of sailing, forecast gust, status, days ahead and the model that scored it (`model_sha256`, the start of the model file's SHA-256), keyed by origin, destination and scheduled departure. `observed_at` is when the prediction was made.
