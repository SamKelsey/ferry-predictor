# ferry-predictor

Predicts whether CalMac ferries to and from Arran (Ardrossan–Brodick and Troon–Brodick) will sail.

This is an unofficial project, not affiliated with CalMac. Always check [CalMac's service status](https://www.calmac.co.uk/service-status) before you travel.

## How it works

- `ferry.poll` runs every 10 minutes on GitHub Actions. It records the status of every sailing in the next eight days, each route's service notices and the vessels assigned to each route. Only changes are written, as rows appended to CSV files on the [`data`](../../tree/data) branch. CalMac drops a cancelled sailing from its timetable rather than marking it cancelled, so when a sailing it was listing disappears before its day is over, the poll logs it with the status `REMOVED`.
- `ferry.predict` takes the next eight days of sailings from CalMac and the latest GFS forecast from [Open-Meteo](https://open-meteo.com/), and writes each sailing's chance of sailing to `predictions.json`. Sailings CalMac has already cancelled get no prediction.
- The site in `web/` is a static React page that reads `predictions.json`. The publish workflow regenerates the predictions and redeploys it to GitHub Pages every hour.
- Each time the publish workflow regenerates the predictions, it also appends any that changed to `predictions.csv` on the `data` branch, with each sailing's days ahead and the model that scored it, so they can later be checked against what actually sailed.
- `ferry.train` fits the model in `models/model.joblib`. It learns from every Arran sailing since March 2021 in CalMac's response to freedom of information request FOI 4377, using the GFS forecasts that existed at the time. Its probabilities are calibrated separately for each day of lead time, against forecasts made that many days before each sailing, so they become less certain further ahead. The FOI data itself is not in this repository.

## Accuracy

On sailings from February 2024 to August 2026, each scored by a model trained only on earlier years:

| Days ahead | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| AUC | 0.787 | 0.785 | 0.773 | 0.755 | 0.734 | 0.719 | 0.726 | 0.691 |

The model only sees weather and the timetable, so it can't foresee breakdowns or crew shortages.

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

Predict the next eight days, optionally logging them to a CSV:

```bash
.venv/bin/python -m ferry.predict models/model.joblib predictions.json data/predictions.csv
```

Run the site locally against fresh predictions:

```bash
.venv/bin/python -m ferry.predict models/model.joblib web/public/predictions.json
cd web && npm install && npm run dev
```

Score the live predictions against what actually sailed, from a checkout of the `data` branch:

```bash
git worktree add data data
.venv/bin/python -m ferry.score data
```

For each sailing that has departed, it takes the latest prediction made before departure at each number of days ahead, and counts the sailing as cancelled if its latest status is `CANCELLED` or `REMOVED`. It prints AUC, Brier score and predicted against actual cancellation rate for each number of days ahead, comparable with the table above, then how often sailings in each ten-point chance band actually sailed.

Retrain, given CalMac's FOI 4377 CSV:

```bash
.venv/bin/python -m ferry.train path/to/foi_4377.csv models/model.joblib
```
