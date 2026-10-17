# ferry-predictor

Predicts whether CalMac ferries to and from Arran (Ardrossan–Brodick and Troon–Brodick) will sail.

This is an unofficial project, not affiliated with CalMac. Always check [CalMac's service status](https://www.calmac.co.uk/service-status) before you travel.

## How it works

- `ferry.poll` runs every 10 minutes on GitHub Actions. It records the status of every sailing in the next eight days, each route's service notices and the vessels assigned to each route. Only changes are written, as rows appended to CSV files on the [`data`](../../tree/data) branch.
- `ferry.predict` takes the next eight days of sailings from CalMac and the latest GFS forecast from [Open-Meteo](https://open-meteo.com/), and writes each sailing's chance of sailing to `predictions.json`. Sailings CalMac has already cancelled get no prediction.
- The site in `web/` is a static React page that reads `predictions.json`. The publish workflow regenerates the predictions and redeploys it to GitHub Pages every hour.
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

Predict the next eight days:

```bash
.venv/bin/python -m ferry.predict models/model.joblib predictions.json
```

Run the site locally against fresh predictions:

```bash
.venv/bin/python -m ferry.predict models/model.joblib web/public/predictions.json
cd web && npm install && npm run dev
```

Retrain, given CalMac's FOI 4377 CSV:

```bash
.venv/bin/python -m ferry.train path/to/foi_4377.csv models/model.joblib
```
