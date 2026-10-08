"""Fills the live review queue from a simulated decision stream.

The cases are the first ``n_cases`` arrivals of one seed's test stream per domain, routed by the
configured policy. Autonomous cases are executed and logged; review and approval cases wait for a
person in the console.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from governance.agent.model import decision_threshold
from governance.api.store import Store
from governance.experiments.stream import build_stream
from governance.humans.reviewer import ReviewerModel, Staffing
from governance.policy.policy import Policy, audit_record, route


def _display(v: Any) -> Any:
    return round(v, 4) if isinstance(v, float) else v


def seed_queue(
    store: Store,
    root: Path,
    domains: Iterable[str] = ("payments", "credit", "eligibility"),
    seed: int = 0,
    n_cases: int = 200,
) -> int:
    added = 0
    for domain in domains:
        policy = Policy.load(root / "configs" / "policies" / f"{domain}.yaml")
        st = build_stream(domain, seed, ReviewerModel(), Staffing())
        d, out = st.ctx.domain, st.ctx.out
        routing = route(policy, d, out)
        model_id = f"{st.agent.model_kind}+{st.agent.calibrator_name}/seed{seed}"
        for j in range(min(n_cases, len(out.idx))):
            i = int(out.idx[j])
            rec = audit_record(policy, d, out, routing, j, model_id)
            rec.update(
                domain=domain,
                positive_action=d.positive_action,
                negative_action=d.negative_action,
                stake_unit=d.stake_unit,
                decision_threshold=decision_threshold(d),
                cost_false_approve=d.cost_false_approve,
                cost_false_decline=d.cost_false_decline,
                policy_rules={r.id: r.description for r in policy.rules},
            )
            store.add_case({
                "id": f"{domain}-{seed}-{j:05d}", "domain": domain, "seq": j, "tier": rec["tier"],
                "priority": rec["expected_cost"], "routing": rec,
                "features": {k: _display(v) for k, v in d.features[i].items()},
                "explanation": st.agent.explain(i) if rec["tier"] != "autonomous" else [],
                "ai_decision": rec["ai_decision"],
                "truth": d.positive_action if d.y[i] == 1 else d.negative_action,
            })  # fmt: skip
            added += 1
    return added
