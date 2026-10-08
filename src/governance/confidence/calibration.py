"""Post-hoc calibrators and calibration metrics.

Calibrators map the model's raw probability of the positive class to a calibrated one and are fitted
on the calibration split only. Metrics are computed on the *decision confidence*: the estimated
probability that the decision actually taken is correct, which is what the router consumes.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

EPS = 1e-6


class Calibrator(Protocol):
    name: str

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> Calibrator: ...
    def transform(self, p_raw: np.ndarray) -> np.ndarray: ...


class Identity:
    name = "none"

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> Identity:
        return self

    def transform(self, p_raw: np.ndarray) -> np.ndarray:
        return np.clip(p_raw, EPS, 1 - EPS)


class Platt:
    """Logistic regression on the logit of the raw score (Platt scaling)."""

    name = "platt"

    def __init__(self) -> None:
        self._lr = LogisticRegression(C=1e6, max_iter=1000)

    @staticmethod
    def _logit(p: np.ndarray) -> np.ndarray:
        p = np.clip(p, EPS, 1 - EPS)
        return np.log(p / (1 - p)).reshape(-1, 1)

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> Platt:
        self._lr.fit(self._logit(p_raw), y)
        return self

    def transform(self, p_raw: np.ndarray) -> np.ndarray:
        out: np.ndarray = self._lr.predict_proba(self._logit(p_raw))[:, 1]
        return np.clip(out, EPS, 1 - EPS)


class Isotonic:
    name = "isotonic"

    def __init__(self) -> None:
        self._iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> Isotonic:
        self._iso.fit(p_raw, y)
        return self

    def transform(self, p_raw: np.ndarray) -> np.ndarray:
        return np.clip(np.asarray(self._iso.predict(p_raw), dtype=float), EPS, 1 - EPS)


CALIBRATORS: dict[str, type[Identity] | type[Platt] | type[Isotonic]] = {
    "none": Identity,
    "platt": Platt,
    "isotonic": Isotonic,
}


def make_calibrator(name: str) -> Calibrator:
    try:
        return CALIBRATORS[name]()
    except KeyError as exc:
        raise ValueError(f"unknown calibrator '{name}' ({', '.join(CALIBRATORS)})") from exc


# --- metrics ----------------------------------------------------------------------------------
def reliability_bins(
    conf: np.ndarray, correct: np.ndarray, n_bins: int = 15
) -> list[dict[str, float]]:
    """Equal-mass bins of confidence with mean confidence, observed accuracy and count."""
    order = np.argsort(conf, kind="stable")
    bins = [b for b in np.array_split(order, min(n_bins, len(conf))) if len(b)]
    return [
        {
            "conf": float(conf[b].mean()),
            "acc": float(correct[b].mean()),
            "count": float(len(b)),
            "lo": float(conf[b].min()),
            "hi": float(conf[b].max()),
        }
        for b in bins
    ]


def ece(conf: np.ndarray, correct: np.ndarray, n_bins: int = 15) -> float:
    """Expected calibration error with equal-mass bins."""
    bins = reliability_bins(conf, correct, n_bins)
    n = len(conf)
    return float(sum(b["count"] / n * abs(b["acc"] - b["conf"]) for b in bins))


def mce(conf: np.ndarray, correct: np.ndarray, n_bins: int = 15) -> float:
    return float(max(abs(b["acc"] - b["conf"]) for b in reliability_bins(conf, correct, n_bins)))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def nll(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
