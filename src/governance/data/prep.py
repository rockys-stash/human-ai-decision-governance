"""Splits and feature encoding. Everything is fitted on the training split only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from governance.data.domains import Domain


@dataclass(frozen=True)
class Split:
    train: np.ndarray
    calib: np.ndarray
    test: np.ndarray

    def check_disjoint(self) -> None:
        a, b, c = set(self.train.tolist()), set(self.calib.tolist()), set(self.test.tolist())
        if a & b or a & c or b & c:
            raise AssertionError("split leakage: overlapping row indices")


def stratified_split(
    y: np.ndarray, seed: int, fractions: tuple[float, float, float] = (0.6, 0.2, 0.2)
) -> Split:
    """Stratified train / calibration / test split of row indices."""
    if abs(sum(fractions) - 1.0) > 1e-9:
        raise ValueError("fractions must sum to 1")
    rng = np.random.default_rng(seed)
    parts: list[list[int]] = [[], [], []]
    for cls in np.unique(y):
        idx = np.flatnonzero(y == cls)
        rng.shuffle(idx)
        n_train = round(fractions[0] * len(idx))
        n_calib = round(fractions[1] * len(idx))
        parts[0] += idx[:n_train].tolist()
        parts[1] += idx[n_train : n_train + n_calib].tolist()
        parts[2] += idx[n_train + n_calib :].tolist()
    out = [np.array(sorted(p), dtype=int) for p in parts]
    # The test split is a *stream*: shuffle its order so arrival order is not sorted by row id.
    rng.shuffle(out[2])
    split = Split(out[0], out[1], out[2])
    split.check_disjoint()
    return split


class Encoder:
    """Standardises numeric features and one-hot encodes categoricals (categories seen in train;
    unseen categories map to all-zero)."""

    def __init__(self, numeric: list[str], categorical: list[str]) -> None:
        self.numeric, self.categorical = numeric, categorical
        self.mean: dict[str, float] = {}
        self.std: dict[str, float] = {}
        self.levels: dict[str, list[str]] = {}

    def fit(self, rows: list[dict[str, Any]]) -> Encoder:
        for k in self.numeric:
            v = np.array([float(r[k]) for r in rows])
            v = self._transform_numeric(k, v)
            self.mean[k], self.std[k] = float(v.mean()), float(v.std() or 1.0)
        for k in self.categorical:
            self.levels[k] = sorted({str(r[k]) for r in rows})
        return self

    @staticmethod
    def _transform_numeric(k: str, v: np.ndarray) -> np.ndarray:
        # Heavy-tailed money amounts are modelled on a log scale.
        if k in {"amount", "credit_amount", "capital_gain", "capital_loss"}:
            return np.log1p(np.maximum(v, 0.0))
        return v

    @property
    def names(self) -> list[str]:
        return list(self.numeric) + [f"{k}={lv}" for k in self.categorical for lv in self.levels[k]]

    def transform(self, rows: list[dict[str, Any]]) -> np.ndarray:
        cols: list[np.ndarray] = []
        for k in self.numeric:
            v = self._transform_numeric(k, np.array([float(r[k]) for r in rows]))
            cols.append((v - self.mean[k]) / self.std[k])
        for k in self.categorical:
            vals = np.array([str(r[k]) for r in rows])
            for lv in self.levels[k]:
                cols.append((vals == lv).astype(float))
        return np.column_stack(cols) if cols else np.zeros((len(rows), 0))


def rows(domain: Domain, idx: np.ndarray) -> list[dict[str, Any]]:
    return [domain.features[i] for i in idx]
