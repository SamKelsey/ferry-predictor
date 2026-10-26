# ferry-predictor

Predicts whether CalMac ferries to and from Arran (Ardrossan–Brodick and Troon–Brodick) will sail.

This is an unofficial project, not affiliated with CalMac. Always check [CalMac's service status](https://www.calmac.co.uk/service-status) before you travel.

## How it works

- `ferry.poll` runs every 10 minutes on GitHub Actions. It records the status of every sailing in the next eight days, each route's service notices, the vessels assigned to each route, and the Met Office's weather warnings for Strathclyde, which can come up to a week ahead. Only changes are written, as rows appended to CSV files on the [`data`](../../tree/data) branch. CalMac drops a cancelled sailing from its timetable rather than marking it cancelled, so when a sailing it was listing disappears before its day is over, the poll logs it with the status `REMOVED`.
- `ferry.forecasts` runs every 3 hours on GitHub Actions and saves each new 00:00 and 12:00 run of three forecasts for the next eight days to `forecasts/` on the `data` branch, every 3 hours of forecast time: ECMWF's main forecast, a summary of ECMWF's 51-member ensemble (gust spread and the share of members over 30, 35 and 40 knots), and Météo-France's wave forecast. Open-Meteo doesn't keep past runs of these, so they're saved now to test against GFS later.
- `ferry.predict` takes the next eight days of sailings from CalMac the latest GFS forecast from [Open-Meteo](https://open-meteo.com/), and each route's cancellations over the last 1, 7 and 28 days from the poll's logs, and writes each sailing's chance of sailing to `predictions.json`. Sailings CalMac has already cancelled get no prediction.
- The site in `web/` is a static React page that reads `predictions.json`. The publish workflow regenerates the predictions and redeploys it to GitHub Pages every hour.
- Each time the publish workflow regenerates the predictions, it also appends any that changed to `predictions.csv` on the `data` branch, with each sailing's days ahead and the model that scored it, so they can later be checked against what actually sailed.
- `ferry.train` fits the model in `models/model.joblib`. It learns from every Arran sailing since March 2021 in CalMac's response to freedom of information request FOI 4405, using the GFS forecasts that existed at the time and each route's recent cancellations. A route's cancellations are known up to the day before a prediction is made, so there is a classifier for each number of days ahead. Its probabilities are calibrated separately for each day of lead time, against forecasts made that many days before each sailing, so they become less certain further ahead. The FOI data itself is not in this repository.

## Accuracy

On sailings from February 2024 to September 2026, each scored by a model trained only on earlier years:

| Days ahead | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| AUC | 0.858 | 0.855 | 0.799 | 0.773 | 0.750 | 0.724 | 0.734 | 0.703 |

The model sees the weather, the timetable and each route's recent cancellations. Recent cancellations make a run of breakdowns predictable for a day or two, but not a first breakdown. Before the poll logged removed sailings on 26 October 2026, a day only counts as cancelled in the logs if a notice cancelled it outright, and days before the poll began on 17 October count as quiet.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest
```

Poll once into a local folder:

```bash
.venv/bin/python -m ferry.poll data
```

Predict the next eight days, logging them to a CSV and reading recent cancellations from a checkout of the `data` branch:

```bash
.venv/bin/python -m ferry.predict models/model.joblib predictions.json data/predictions.csv data
```

Run the site locally against fresh predictions:

```bash
.venv/bin/python -m ferry.predict models/model.joblib web/public/predictions.json
cd web && npm install && npm run dev
```

Save the latest forecast runs into a local folder:

```bash
.venv/bin/python -m ferry.forecasts data
```

Score the live predictions against what actually sailed, from a checkout of the `data` branch:

```bash
git worktree add data data
.venv/bin/python -m ferry.score data
```

For each sailing that has departed, it takes the latest prediction made before departure at each number of days ahead, and counts the sailing as cancelled if its latest status is `CANCELLED` or `REMOVED`. It prints AUC, Brier score and predicted against actual cancellation rate for each number of days ahead, comparable with the table above, then how often sailings in each ten-point chance band actually sailed.

Retrain, given CalMac's FOI 4405 CSV:

```bash
.venv/bin/python -m ferry.train path/to/foi_4405.csv models/model.joblib
```
