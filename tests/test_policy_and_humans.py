from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from governance.agent.model import AgentOutput
from governance.data.domains import Domain, make_synthetic
from governance.humans.reviewer import (
    CaseDraws,
    Mode,
    ReviewerModel,
    Staffing,
    judge,
    simulate_queue,
)
from governance.policy.policy import TIERS, Policy, audit_record, route

ROOT = Path(__file__).resolve().parents[1]


def _out(domain: Domain, idx: np.ndarray, p: np.ndarray) -> AgentOutput:
    decision = (p >= 0.8).astype(int)
    conf = np.where(decision == 1, p, 1 - p)
    cost = domain.cost_if_wrong(decision, domain.stake[idx])
    return AgentOutput(idx, p, p, decision, conf, (1 - conf) * cost)


def test_policies_in_repo_are_valid_and_hash_stable() -> None:
    for name in ("credit", "eligibility", "payments"):
        p = Policy.load(ROOT / "configs" / "policies" / f"{name}.yaml")
        assert p.domain == name and len(p.hash) == 12
        assert p.hash == Policy.load(ROOT / "configs" / "policies" / f"{name}.yaml").hash
        assert p.with_thresholds(1, 2).hash != p.hash


def test_threshold_order_is_validated() -> None:
    with pytest.raises(ValidationError):
        Policy.model_validate({"id": "x", "version": "1", "domain": "d", "description": "",
                               "thresholds": {"review": 5, "approval": 1}})  # fmt: skip


def test_routing_tiers_and_rules_only_raise() -> None:
    d = make_synthetic(n=50, seed=0)
    idx = np.arange(5)
    d.stake[idx] = [100, 100, 100, 50000, 100]
    d.features[4]["new_bank_details"] = 1
    for i in range(4):
        d.features[i]["new_bank_details"] = 0
    p = np.array([0.99, 0.85, 0.5, 0.99, 0.99])
    policy = Policy.model_validate({
        "id": "t", "version": "1", "domain": "payments", "description": "",
        "thresholds": {"review": 5, "approval": 30},
        "rules": [
            {"id": "big", "description": "", "route": "approval", "when": [{"field": "stake", "op": "gte", "value": 20000}]},
            {"id": "bank", "description": "", "route": "review", "when": [{"field": "feature:new_bank_details", "op": "eq", "value": 1}]},
        ],
    })  # fmt: skip
    out = _out(d, idx, p)
    r = route(policy, d, out)
    # expected costs: 1, 15, 25 (reject: 0.5 x 0.25 x 100 = 12.5), 500, 1
    assert [TIERS[t] for t in r.cost_tier] == [
        "autonomous",
        "review",
        "review",
        "approval",
        "autonomous",
    ]
    assert [TIERS[t] for t in r.tier] == ["autonomous", "review", "review", "approval", "review"]
    assert r.rules_fired[3] == ["big"] and r.rules_fired[4] == ["bank"]
    rec = audit_record(policy, d, out, r, 4, "m")
    assert (
        rec["policy_hash"] == policy.hash
        and rec["tier"] == "review"
        and rec["cost_tier"] == "autonomous"
    )


def test_reviewer_decision_procedure() -> None:
    m = ReviewerModel(acc_easy=1.0, acc_hard=1.0, review_accuracy_penalty=0.0,
                      automation_bias_review=0.5, automation_bias_approval=0.0)  # fmt: skip
    # Perfect reviewer, AI wrong: approval mode always overrides; review mode defers when u < 0.5.
    assert judge(m, "approval", y=1, ai=0, d=0.5, fatigue=0, u_judge=0.3, u_defer=0.1) == (
        1,
        "override",
    )
    assert judge(m, "review", y=1, ai=0, d=0.5, fatigue=0, u_judge=0.3, u_defer=0.1) == (0, "defer")
    assert judge(m, "review", y=1, ai=1, d=0.5, fatigue=0, u_judge=0.3, u_defer=0.1) == (
        1,
        "accept",
    )
    assert judge(m, "unaided", y=0, ai=1, d=0.5, fatigue=0, u_judge=0.3, u_defer=0.1) == (
        0,
        "unaided",
    )


def test_queue_respects_capacity_priority_and_causality() -> None:
    n = 200
    rng = np.random.default_rng(0)
    draws = CaseDraws.draw(n, rng, arrivals_per_hour=60)
    modes: list[Mode | None] = [
        "approval" if i % 3 == 0 else ("review" if i % 3 == 1 else None) for i in range(n)
    ]
    y = rng.integers(0, 2, n)
    res = simulate_queue(
        ReviewerModel(),
        Staffing(reviewers=2, arrivals_per_hour=60),
        modes,
        y,
        y.copy(),
        np.zeros(n),
        draws,
    )
    human = np.array([m is not None for m in modes])
    assert np.all(res.start_min[human] >= draws.arrival_min[human] - 1e-9)
    assert np.all(res.end_min >= res.start_min)
    assert set(res.reviewer[human]) <= {0, 1} and np.all(res.reviewer[~human] == -1)
    # No reviewer works two cases at once.
    for r in (0, 1):
        js = np.flatnonzero(res.reviewer == r)
        s, e = res.start_min[js], res.end_min[js]
        order = np.argsort(s)
        assert np.all(s[order][1:] >= e[order][:-1] - 1e-9)
    # AI is always right here and the reviewer never errs on easy cases often: decisions mostly kept.
    assert (res.decision == y).mean() > 0.9
