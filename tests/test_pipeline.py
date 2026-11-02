"""python3 -m pytest tests  (downloads the weights on first run)"""
import numpy as np

from anemia_eye import AnemiaEye
from anemia_eye.pipeline import CALIBRATION

eye = AnemiaEye(device='cpu')


def test_score_is_monotonic():
    # A paler conjunctiva (lower a_norm) must never give a lower probability of anemia.
    p = [eye.score(a)[0] for a in np.linspace(-5, 25, 50)]
    assert all(x >= y for x, y in zip(p, p[1:]))


def test_triage_thresholds():
    assert eye.score(30)[1] == 'green'
    assert eye.score(-10)[1] == 'red'
    assert CALIBRATION['t_green'] < CALIBRATION['t_red']


def test_rejects_unusable_images():
    assert not eye.predict(None).ok
    assert not eye.predict(np.zeros((800, 800, 3), np.uint8)).ok                  # too dark
    assert not eye.predict(np.full((100, 100, 3), 128, np.uint8)).ok              # too small
    noise = np.random.default_rng(0).integers(0, 255, (800, 800, 3), dtype=np.uint8)
    assert not eye.predict(noise).ok                                               # no conjunctiva
