"""The AI agent: a classifier that proposes the case decision, plus its confidence estimator.

The governance layer is agent-agnostic: it consumes (decision, calibrated confidence) pairs. The
agent here is a tabular classifier because the decisions are tabular; an LLM agent would plug into
the same interface by providing a raw probability for the positive action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from governance.confidence.calibration import Calibrator, make_calibrator
from governance.data.domains import Domain
from governance.data.prep import Encoder, Split, rows


def make_model(kind: str, seed: int) -> Any:
    if kind == "gbm":
        return HistGradientBoostingClassifier(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=15, random_state=seed
        )
    if kind == "logreg":
        return LogisticRegression(C=1.0, max_iter=2000)
    raise ValueError(f"unknown model '{kind}' (gbm, logreg)")


@dataclass
class AgentOutput:
    """Per-case agent output on a set of rows (aligned with ``idx``)."""

    idx: np.ndarray
    p_raw: np.ndarray
    p: np.ndarray  # calibrated probability that the positive action is correct
    decision: np.ndarray  # 1 = positive action
    confidence: np.ndarray  # estimated probability that ``decision`` is correct
    expected_cost: np.ndarray  # (1 - confidence) x cost if wrong


def decision_threshold(domain: Domain) -> float:
    """Bayes threshold on p for taking the positive action, from the domain's error costs."""
    return domain.cost_false_approve / (domain.cost_false_approve + domain.cost_false_decline)


class DecisionAgent:
    def __init__(
        self, domain: Domain, model: str = "gbm", calibrator: str = "isotonic", seed: int = 0
    ):
        self.domain, self.model_kind, self.calibrator_name, self.seed = (
            domain,
            model,
            calibrator,
            seed,
        )
        self.encoder = Encoder(domain.numeric, domain.categorical)
        self.model: Any = None
        self.calibrator: Calibrator = make_calibrator(calibrator)
        self.threshold = decision_threshold(domain)
        self._modes: dict[str, str] = {}

    def fit(self, split: Split) -> DecisionAgent:
        train_rows = rows(self.domain, split.train)
        self.encoder.fit(train_rows)
        self._modes = {
            k: max(
                sorted({str(r[k]) for r in train_rows}), key=[str(r[k]) for r in train_rows].count
            )
            for k in self.domain.categorical
        }
        self.model = make_model(self.model_kind, self.seed)
        self.model.fit(self.encoder.transform(train_rows), self.domain.y[split.train])
        self.calibrator.fit(self.raw(split.calib), self.domain.y[split.calib])
        return self

    def raw(self, idx: np.ndarray) -> np.ndarray:
        X = self.encoder.transform(rows(self.domain, idx))
        return np.asarray(self.model.predict_proba(X)[:, 1], dtype=float)

    def predict(self, idx: np.ndarray) -> AgentOutput:
        p_raw = self.raw(idx)
        p = self.calibrator.transform(p_raw)
        return self.outputs(idx, p_raw, p)

    def outputs(self, idx: np.ndarray, p_raw: np.ndarray, p: np.ndarray) -> AgentOutput:
        decision = (p >= self.threshold).astype(int)
        confidence = np.where(decision == 1, p, 1 - p)
        cost = self.domain.cost_if_wrong(decision, self.domain.stake[idx])
        return AgentOutput(idx, p_raw, p, decision, confidence, (1 - confidence) * cost)

    def explain(self, i: int, top: int = 5) -> list[dict[str, Any]]:
        """Local evidence for one case: change in the model's raw score when each feature is replaced
        by its training reference value (mean / most common level). Model-agnostic and cheap; the raw
        score is used because calibrated probabilities can be piecewise constant (isotonic)."""
        base_row = self.domain.features[i]
        base = float(self._p_rows([base_row])[0])
        out = []
        for k in self.domain.numeric + self.domain.categorical:
            ref = self._reference(k)
            if str(base_row[k]) == str(ref):
                continue
            alt = dict(base_row)
            alt[k] = ref
            p_alt = float(self._p_rows([alt])[0])
            out.append(
                {"feature": k, "value": base_row[k], "reference": ref, "effect": base - p_alt}
            )
        out.sort(key=lambda d: -abs(d["effect"]))
        return out[:top]

    def _p_rows(self, rs: list[dict[str, Any]]) -> np.ndarray:
        return np.asarray(self.model.predict_proba(self.encoder.transform(rs))[:, 1], dtype=float)

    def _reference(self, k: str) -> Any:
        if k in self.domain.numeric:
            # Reverse the encoder's standardisation: the training mean on the modelled scale.
            m = self.encoder.mean[k]
            if k in {"amount", "credit_amount", "capital_gain", "capital_loss"}:
                return round(float(np.expm1(m)), 2)
            return round(m, 2)
        return self._modes[k]


def reference_probability(domain: Domain, split: Split, idx: np.ndarray, seed: int) -> np.ndarray:
    """Probability from an independent reference model (logistic regression, train split only),
    used to grade case difficulty for the simulated reviewers. For the synthetic domain the true
    probability is used instead."""
    if domain.true_p is not None:
        return domain.true_p[idx]
    enc = Encoder(domain.numeric, domain.categorical).fit(rows(domain, split.train))
    lr = make_model("logreg", seed).fit(
        enc.transform(rows(domain, split.train)), domain.y[split.train]
    )
    return np.asarray(lr.predict_proba(enc.transform(rows(domain, idx)))[:, 1], dtype=float)
