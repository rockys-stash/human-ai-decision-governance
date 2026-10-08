from __future__ import annotations

import numpy as np
import pytest

from governance.agent.model import DecisionAgent, decision_threshold
from governance.confidence.calibration import Isotonic, Platt, brier, ece, reliability_bins
from governance.data.domains import load_adult, load_german, make_synthetic, synthetic_true_p
from governance.data.prep import Encoder, stratified_split


def test_real_datasets_load_with_documented_shape() -> None:
    g, a = load_german(), load_adult()
    assert (g.n, int(g.y.sum())) == (1000, 700)  # 700 good / 300 bad credits
    assert a.n == 48842 and abs(a.y.mean() - 37155 / 48842) < 1e-12
    assert g.stake.min() > 0 and set(g.groups["sex"]) == {"female", "male"}


def test_checksum_is_enforced(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "german.csv").write_text("A11,6\n")
    with pytest.raises(ValueError, match="checksum"):
        load_german(tmp_path)


def test_split_is_disjoint_stratified_and_deterministic() -> None:
    y = np.array([0] * 300 + [1] * 700)
    s1, s2 = stratified_split(y, 5), stratified_split(y, 5)
    assert np.array_equal(s1.test, s2.test)
    assert len(s1.train) + len(s1.calib) + len(s1.test) == 1000
    s1.check_disjoint()
    for part in (s1.train, s1.calib, s1.test):
        assert abs(y[part].mean() - 0.7) < 0.01


def test_encoder_fits_on_train_only() -> None:
    rows = [{"x": 1.0, "c": "a"}, {"x": 3.0, "c": "b"}]
    enc = Encoder(["x"], ["c"]).fit(rows)
    out = enc.transform([{"x": 2.0, "c": "unseen"}])
    assert out.shape == (1, 3) and out[0, 0] == 0.0 and out[0, 1:].sum() == 0


def test_synthetic_domain_matches_its_generative_model() -> None:
    d = make_synthetic(n=20000, seed=3)
    assert abs(d.y.mean() - d.true_p.mean()) < 0.01  # type: ignore[union-attr]
    risky = dict(d.features[0], vendor_risk_score=0.9, invoice_mismatch=1)
    safe = dict(d.features[0], vendor_risk_score=0.0, invoice_mismatch=0)
    assert synthetic_true_p(risky) < synthetic_true_p(safe)
    shifted = dict(safe, new_bank_details=1)
    assert synthetic_true_p(shifted, shift=1.0) < synthetic_true_p(shifted)


def test_calibration_metrics() -> None:
    rng = np.random.default_rng(0)
    conf = rng.uniform(0.5, 1.0, 20000)
    correct = (rng.random(20000) < conf).astype(float)
    assert ece(conf, correct) < 0.02  # calibrated by construction
    assert ece(np.full(20000, 0.99), correct) > 0.2  # overconfident
    bins = reliability_bins(conf, correct, 10)
    assert len(bins) == 10 and sum(b["count"] for b in bins) == 20000
    assert brier(np.array([1.0, 0.0]), np.array([1, 0])) == 0.0


@pytest.mark.parametrize("cal", [Platt, Isotonic])
def test_calibrators_repair_a_distorted_score(cal: type) -> None:
    rng = np.random.default_rng(1)
    p_true = rng.uniform(0.05, 0.95, 20000)
    y = (rng.random(20000) < p_true).astype(int)
    distorted = p_true**3  # badly miscalibrated but monotone
    fitted = cal().fit(distorted[:10000], y[:10000]).transform(distorted[10000:])
    assert brier(fitted, y[10000:]) < brier(distorted[10000:], y[10000:]) - 0.01


def test_agent_decides_with_the_cost_threshold() -> None:
    d = make_synthetic(n=5000, seed=2)
    split = stratified_split(d.y, 0)
    agent = DecisionAgent(d, "logreg", "platt", 0).fit(split)
    out = agent.predict(split.test)
    t = decision_threshold(d)
    assert t == pytest.approx(1 / 1.25)
    assert np.all((out.p >= t) == (out.decision == 1))
    assert np.all(out.confidence[out.decision == 1] >= t) and np.all(
        out.confidence[out.decision == 0] > 1 - t
    )
    expected = (1 - out.confidence) * d.cost_if_wrong(out.decision, d.stake[split.test])
    assert np.allclose(out.expected_cost, expected)
    ev = agent.explain(int(split.test[0]))
    assert ev and {"feature", "value", "reference", "effect"} <= set(ev[0])
