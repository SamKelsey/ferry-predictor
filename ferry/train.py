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


def main(foi_path: Path, model_path: Path) -> None:
    sailings = features.timetable(foi.sailings(foi_path))
    sailings = sailings[sailings.departs >= ARCHIVE_START].reset_index(drop=True)
    end = sailings.departs.max().date() + timedelta(days=1)
    forecasts = {0: openmeteo.archive(ARCHIVE_START.date(), end), **openmeteo.previous_runs(PREVIOUS_RUNS_START.date(), end)}
    X = {lead: features.build(features.local(forecasts[lead]), sailings) for lead in LEADS}
    y = sailings.cancelled

    scores, cancelled = out_of_sample(X, y, sailings.departs.dt.year)
    for lead in LEADS:
        print(f'{lead} days ahead: AUC {roc_auc_score(cancelled, scores[lead]):.3f} on {len(cancelled)} sailings')

    model.save(model.Model(
        classifier=model.classifier().fit(X[0], y),
        calibrations={lead: model.calibration(scores[lead], cancelled) for lead in LEADS},
    ), model_path)


def out_of_sample(X: dict[int, pd.DataFrame], y: pd.Series, years: pd.Series) -> tuple[dict[int, np.ndarray], pd.Series]:
    """Scores at every lead for each sailing since previous runs began, each from a classifier trained only on earlier years."""
    has_every_lead = np.logical_and.reduce([X[lead].port_gust_window.notna() for lead in LEADS])
    scores: dict[int, list[np.ndarray]] = {lead: [] for lead in LEADS}
    outcomes = []
    for year in range(PREVIOUS_RUNS_START.year, years.max() + 1):
        test = has_every_lead & (years == year)
        classifier = model.classifier().fit(X[0][years < year], y[years < year])
        for lead in LEADS:
            scores[lead].append(classifier.predict_proba(X[lead][test])[:, 1])
        outcomes.append(y[test])
    return {lead: np.concatenate(s) for lead, s in scores.items()}, pd.concat(outcomes)


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))
