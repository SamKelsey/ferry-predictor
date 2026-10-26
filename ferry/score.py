import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from ferry import poll

SAILING = ['origin', 'destination', 'departs']


def main(data_dir: Path) -> None:
    predictions = pd.read_csv(data_dir / 'predictions.csv', dtype=str)
    sailings = pd.read_csv(data_dir / 'sailings.csv', dtype=str)
    table = scored(predictions, sailings, pd.Timestamp(datetime.now(timezone.utc)))
    if table.empty:
        print('No departed sailings have a prediction yet.')
        return
    print(by_lead(table).to_string(index=False))
    print()
    print(by_band(table).to_string(index=False))


def scored(predictions: pd.DataFrame, sailings: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """Each departed sailing's latest prediction before departure at each number of days ahead, with whether CalMac cancelled it."""
    predictions = predictions[predictions.chance_of_sailing.fillna('') != '']
    predictions = predictions.assign(
        made_at=pd.to_datetime(predictions.observed_at, utc=True),
        departs_at=pd.to_datetime(predictions.departs, utc=True),
        days_ahead=predictions.days_ahead.astype(int),
        chance_of_sailing=predictions.chance_of_sailing.astype(float),
    )
    predictions = predictions[predictions.made_at < predictions.departs_at]
    latest = predictions.sort_values('made_at').groupby([*SAILING, 'days_ahead']).tail(1)

    final = sailings.assign(seen_at=pd.to_datetime(sailings.observed_at, utc=True)).sort_values('seen_at').groupby(SAILING).tail(1)
    final = final[pd.to_datetime(final.departs, utc=True) < now].assign(cancelled=final.status.isin(['CANCELLED', poll.REMOVED]))

    table = latest.merge(final[[*SAILING, 'cancelled']], on=SAILING)
    return table[[*SAILING, 'days_ahead', 'chance_of_sailing', 'cancelled']].sort_values([*SAILING, 'days_ahead']).reset_index(drop=True)


def by_lead(table: pd.DataFrame) -> pd.DataFrame:
    """AUC, Brier score and predicted against actual cancellation rate for each number of days ahead."""
    rows = []
    for days_ahead, group in table.groupby('days_ahead'):
        risk = 1 - group.chance_of_sailing
        both_outcomes = group.cancelled.nunique() == 2
        rows.append({
            'days_ahead': days_ahead,
            'sailings': len(group),
            'cancelled': int(group.cancelled.sum()),
            'auc': round(roc_auc_score(group.cancelled, risk), 3) if both_outcomes else np.nan,
            'brier': round(brier_score_loss(group.cancelled, risk), 4),
            'predicted_cancel_rate': round(risk.mean(), 3),
            'actual_cancel_rate': round(group.cancelled.mean(), 3),
        })
    return pd.DataFrame(rows)


def by_band(table: pd.DataFrame) -> pd.DataFrame:
    """Predictions at every number of days ahead grouped into ten-point chance-of-sailing bands, with the share that sailed in each."""
    lower = (np.floor(table.chance_of_sailing * 10).clip(upper=9) * 10).astype(int)
    grouped = table.assign(sailed=~table.cancelled).groupby(lower)
    return pd.DataFrame({
        'chance_of_sailing': [f'{b}–{b + 10}%' for b in grouped.groups],
        'predictions': grouped.size().to_numpy(),
        'predicted_chance': grouped.chance_of_sailing.mean().round(3).to_numpy(),
        'sailed': grouped.sailed.mean().round(3).to_numpy(),
    })


if __name__ == '__main__':
    main(Path(sys.argv[1]))
