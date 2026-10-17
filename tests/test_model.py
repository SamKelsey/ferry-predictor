import numpy as np
import pytest

from ferry import model


class Fixed:
    def __init__(self, value: float):
        self.value = value

    def predict_proba(self, rows):
        return np.column_stack([1 - np.full(len(rows), self.value), np.full(len(rows), self.value)])


CALIBRATED = model.Model(classifier=Fixed(0.5), calibrations={lead: Fixed(lead / 10) for lead in range(model.MAX_LEAD + 1)})


@pytest.mark.parametrize('leads, expected', [
    pytest.param([3], [0.3], id='uses the calibration for its lead'),
    pytest.param([0, 5], [0.01, 0.5], id='never fully certain'),
    pytest.param([12], [0.7], id='leads beyond a week use the longest'),
    pytest.param([-1], [0.01], id='past sailings use same-day'),
])
def test_risk(leads, expected):
    features = np.zeros((len(leads), 1))
    assert model.risk(CALIBRATED, features, np.array(leads)) == pytest.approx(expected)
