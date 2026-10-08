"""Statistics over seeds. Each seed is an independent replication (new data split, newly fitted
agent and calibrator, new reviewer draws), so seeds are the unit of resampling."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


def aggregate(values: Sequence[float | None], n_boot: int = 2000, seed: int = 0) -> dict[str, Any]:
    """Mean, std across seeds and a 95% bootstrap CI of the mean. ``None`` values are skipped."""
    v = np.array([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if v.size == 0:
        return {"mean": None, "std": None, "ci_low": None, "ci_high": None, "n": 0}
    rng = np.random.default_rng(seed)
    boots = v[rng.integers(0, v.size, size=(n_boot, v.size))].mean(axis=1)
    return {
        "mean": float(v.mean()),
        "std": float(v.std(ddof=1)) if v.size > 1 else None,
        "ci_low": float(np.percentile(boots, 2.5)),
        "ci_high": float(np.percentile(boots, 97.5)),
        "n": int(v.size),
    }


def paired_test(
    a: Sequence[float], b: Sequence[float], n_boot: int = 2000, n_perm: int = 10000, seed: int = 0
) -> dict[str, Any]:
    """Mean paired difference a - b over seeds, bootstrap 95% CI, two-sided sign-flip p-value."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if d.size == 0:
        return {"diff": None, "ci_low": None, "ci_high": None, "p_value": 1.0, "n": 0}
    rng = np.random.default_rng(seed)
    boots = d[rng.integers(0, d.size, size=(n_boot, d.size))].mean(axis=1)
    observed = abs(d.mean())
    signs = rng.choice((-1.0, 1.0), size=(n_perm, d.size))
    perm = np.abs((signs * d).mean(axis=1))
    p = (np.sum(perm >= observed - 1e-12) + 1) / (n_perm + 1)
    return {
        "diff": float(d.mean()),
        "ci_low": float(np.percentile(boots, 2.5)),
        "ci_high": float(np.percentile(boots, 97.5)),
        "p_value": float(p),
        "n": int(d.size),
    }


def holm(p: Sequence[float]) -> list[float]:
    """Holm step-down adjusted p-values (same order as the input)."""
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adjusted[i] = running
    return adjusted.tolist()
