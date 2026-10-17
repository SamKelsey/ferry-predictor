from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

MAX_LEAD = 7


@dataclass(frozen=True)
class Model:
    classifier: HistGradientBoostingClassifier
    calibrations: dict[int, LogisticRegression]


def classifier() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=100, l2_regularization=1.0, random_state=0,
    )


def calibration(scores: np.ndarray, cancelled: pd.Series) -> LogisticRegression:
    """A smooth curve from classifier scores to the share of sailings with that score that were cancelled."""
    return LogisticRegression().fit(_logit(scores), cancelled)


def risk(model: Model, features: pd.DataFrame, leads: np.ndarray) -> np.ndarray:
    """The chance each sailing is cancelled, calibrated for how many days ahead its forecast was made, never fully certain."""
    scores = model.classifier.predict_proba(features)[:, 1]
    leads = np.clip(leads, 0, MAX_LEAD)
    calibrated = np.empty(len(scores))
    for lead, calibration_for_lead in model.calibrations.items():
        rows = leads == lead
        if rows.any():
            calibrated[rows] = calibration_for_lead.predict_proba(_logit(scores[rows]))[:, 1]
    return np.clip(calibrated, 0.01, 0.99)


def save(model: Model, path: Path) -> None:
    joblib.dump(model, path)


def load(path: Path) -> Model:
    return joblib.load(path)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p)).reshape(-1, 1)
