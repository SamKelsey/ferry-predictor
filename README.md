# ferry-predictor

Predicts whether CalMac ferries to and from Arran (Ardrossan–Brodick and Troon–Brodick) will sail.

This is an unofficial project, not affiliated with CalMac. Always check [CalMac's service status](https://www.calmac.co.uk/service-status) before you travel.

## How it works

`ferry.poll` runs every 10 minutes on GitHub Actions. It records the status of every sailing in the next eight days, each route's service notices and the vessels assigned to each route. Only changes are written, as rows appended to CSV files on the [`data`](../../tree/data) branch.

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
