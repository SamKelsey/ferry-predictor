import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ferry import features, foi, model, openmeteo

ARCHIVE_START = pd.Timestamp('2021-03-23')
PREVIOUS_RUNS_START = pd.Timestamp('2024-02-01')
LEADS = range(model.MAX_LEAD + 1)
# Same-day and next-day predictions both see cancellations up to the day before they're made.
DAYS_BEFORE = range(1, model.MAX_LEAD + 1)


def main(foi_path: Path, model_path: Path) -> None:
    every = features.timetable(foi.sailings(foi_path))
    outcomes = every[['route', 'date', 'cancelled']]
    sailings = every[every.departs >= ARCHIVE_START].reset_index(drop=True)
    end = sailings.departs.max().date() + timedelta(days=1)
    forecasts = {0: openmeteo.archive(ARCHIVE_START.date(), end), **openmeteo.previous_runs(PREVIOUS_RUNS_START.date(), end)}
    # Each lead's classifier learns from same-day weather and the recent cancellations known that many days ahead,
    # and is scored on the forecast actually made that many days ahead.
    learn = {lead: features.build(features.local(forecasts[0]), sailings, outcomes, lead) for lead in LEADS}
    ahead = {lead: features.build(features.local(forecasts[lead]), sailings, outcomes, lead) for lead in LEADS}
    y = sailings.cancelled

    scores, cancelled = out_of_sample(learn, ahead, y, sailings.departs.dt.year)
    for lead in LEADS:
        print(f'{lead} days ahead: AUC {roc_auc_score(cancelled, scores[lead]):.3f} on {len(cancelled)} sailings')

    fitted = {days_before: model.classifier().fit(learn[days_before], y) for days_before in DAYS_BEFORE}
    model.save(model.Model(
        classifiers={lead: fitted[max(lead, 1)] for lead in LEADS},
        calibrations={lead: model.calibration(scores[lead], cancelled) for lead in LEADS},
    ), model_path)


def out_of_sample(learn: dict[int, pd.DataFrame], ahead: dict[int, pd.DataFrame], y: pd.Series, years: pd.Series) -> tuple[dict[int, np.ndarray], pd.Series]:
    """Scores at every lead for each sailing since previous runs began, each from classifiers trained only on earlier years."""
    has_every_lead = np.logical_and.reduce([ahead[lead].port_gust_window.notna() for lead in LEADS])
    scores: dict[int, list[np.ndarray]] = {lead: [] for lead in LEADS}
    outcomes = []
    for year in range(PREVIOUS_RUNS_START.year, years.max() + 1):
        test = has_every_lead & (years == year)
        earlier = years < year
        classifiers = {d: model.classifier().fit(learn[d][earlier], y[earlier]) for d in DAYS_BEFORE}
        for lead in LEADS:
            scores[lead].append(classifiers[max(lead, 1)].predict_proba(ahead[lead][test])[:, 1])
        outcomes.append(y[test])
    return {lead: np.concatenate(s) for lead, s in scores.items()}, pd.concat(outcomes)


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
