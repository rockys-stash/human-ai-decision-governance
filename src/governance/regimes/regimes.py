"""Oversight regimes and routing baselines, and the per-run outcome metrics.

A *regime* maps each case in the test stream to an oversight mode: ``None`` (the AI decision is
executed autonomously), ``"review"``, ``"approval"`` or ``"unaided"`` (a human decides without the AI).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from governance.agent.model import AgentOutput
from governance.data.domains import Domain
from governance.humans.reviewer import (
    CaseDraws,
    HumanResult,
    Mode,
    ReviewerModel,
    Staffing,
    simulate_queue,
)
from governance.policy.policy import TIERS, Policy, Routing, route

REGIMES = ("human_only", "ai_only", "blanket_approval", "risk_adaptive")
REGIME_LABELS = {
    "human_only": "Human only",
    "ai_only": "AI only",
    "blanket_approval": "AI + blanket approval",
    "risk_adaptive": "Risk-adaptive oversight",
}


@dataclass
class StreamContext:
    """Everything a regime needs about one seed's test stream."""

    domain: Domain
    out: AgentOutput  # calibrated agent output on the test stream
    out_uncal: AgentOutput  # same model, uncalibrated confidence
    difficulty: np.ndarray
    draws: CaseDraws
    reviewer: ReviewerModel
    staffing: Staffing
    high_stake_cut: (
        float | None
    )  # stake above which a case counts as high-stakes (from train split)

    @property
    def y(self) -> np.ndarray:
        return self.domain.y[self.out.idx]

    @property
    def stake(self) -> np.ndarray:
        return self.domain.stake[self.out.idx]


def modes_for_regime(
    regime: str, ctx: StreamContext, policy: Policy
) -> tuple[list[Mode | None], Routing | None]:
    n = len(ctx.out.idx)
    if regime == "ai_only":
        return [None] * n, None
    if regime == "human_only":
        return ["unaided"] * n, None
    if regime == "blanket_approval":
        return ["approval"] * n, None
    if regime == "risk_adaptive":
        r = route(policy, ctx.domain, ctx.out)
        tier_mode: dict[int, Mode | None] = {0: None, 1: "review", 2: "approval"}
        return [tier_mode[int(t)] for t in r.tier], r
    raise ValueError(f"unknown regime '{regime}'")


# --- single-threshold routers for the frontier / ablation experiment (E3) ----------------------
def routing_scores(
    name: str, ctx: StreamContext, out: AgentOutput, rng: np.random.Generator
) -> np.ndarray:
    """Higher score = more in need of a human. ``out`` is the stream (or calibration) output."""
    stake = ctx.domain.stake[out.idx]
    if name == "expected_cost":
        return out.expected_cost
    if name == "confidence_only":
        return 1.0 - out.confidence
    if name == "stake_only":
        return stake.astype(float)
    if name == "random":
        return rng.random(len(out.idx))
    raise ValueError(name)


ROUTERS = ("expected_cost", "expected_cost_uncalibrated", "confidence_only", "stake_only", "random")


def run_modes(ctx: StreamContext, modes: list[Mode | None]) -> HumanResult:
    return simulate_queue(
        ctx.reviewer, ctx.staffing, modes, ctx.y, ctx.out.decision, ctx.difficulty, ctx.draws
    )


def outcome_metrics(
    ctx: StreamContext, modes: list[Mode | None], res: HumanResult, routing: Routing | None = None
) -> dict[str, Any]:
    y, ai, final = ctx.y, ctx.out.decision, res.decision
    n = len(y)
    cost = np.asarray(ctx.domain.error_cost(final, y, ctx.stake), dtype=float)
    wrong = final != y
    human = np.array([m is not None for m in modes])
    shown = np.array([m in ("review", "approval") for m in modes])
    ai_wrong = ai != y
    act = res.action
    overrides = act == "override"
    accepted = (act == "accept") | (act == "defer")
    wait = res.start_min - ctx.draws.arrival_min
    dtime = np.where(human, res.end_min - ctx.draws.arrival_min, 0.0)

    m: dict[str, Any] = {
        "n": n,
        "accuracy": float(1 - wrong.mean()),
        "error_rate": float(wrong.mean()),
        "loss_per_1000": float(cost.sum() / n * 1000),
        "share_human": float(human.mean()),
        "reviewer_hours_per_1000": float(res.handling_min.sum() / 60 / n * 1000),
        "decision_minutes_median": float(np.median(dtime)),
        "decision_minutes_p95": float(np.percentile(dtime, 95)),
        "human_decision_minutes_median": float(np.median(dtime[human])) if human.any() else None,
        "wait_minutes_p95": float(np.percentile(wait[human], 95)) if human.any() else None,
        "utilisation": res.utilisation,
        "queue_peak": res.queue_peak,
        # Oversight behaviour on cases where the AI decision was shown to a reviewer.
        "override_rate": float(overrides[shown].mean()) if shown.any() else None,
        "override_precision": float((final[overrides] == y[overrides]).mean()) if overrides.any() else None,
        "automation_bias_rate": float(accepted[shown & ai_wrong].mean()) if (shown & ai_wrong).any() else None,
        "appropriate_reliance": float(
            ((accepted & ~ai_wrong) | (overrides & ai_wrong))[shown].mean()
        ) if shown.any() else None,
        # Error attribution: every wrong final decision gets exactly one cause.
        "errors": {
            "autonomous_ai_error": int((wrong & ~human).sum()),
            "accepted_wrong_ai": int((wrong & shown & accepted).sum()),
            "harmful_override": int((wrong & shown & overrides).sum()),
            "unaided_human_error": int((wrong & (act == "unaided")).sum()),
        },
    }  # fmt: skip
    if ctx.high_stake_cut is not None:
        hs = ctx.stake >= ctx.high_stake_cut
        m["high_stake_errors_per_1000"] = float(int((wrong & hs).sum()) / n * 1000)
        total = float(cost.sum())
        m["high_stake_loss_share"] = float(cost[hs].sum()) / total if total > 0 else 0.0
    if routing is not None:
        m["tier_share"] = {t: float((routing.tier == i).mean()) for i, t in enumerate(TIERS)}
        fired: dict[str, int] = {}
        for rs in routing.rules_fired:
            for r in rs:
                fired[r] = fired.get(r, 0) + 1
        m["rules_fired"] = fired
        m["error_by_tier"] = {
            t: float(wrong[routing.tier == i].mean()) if (routing.tier == i).any() else None
            for i, t in enumerate(TIERS)
        }
    groups = {}
    for gname, gvals in ctx.domain.groups.items():
        gv = gvals[ctx.out.idx]
        groups[gname] = {
            str(g): {
                "n": int((gv == g).sum()),
                "error_rate": float(wrong[gv == g].mean()),
                "share_human": float(human[gv == g].mean()),
            }
            for g in np.unique(gv)
            if (gv == g).sum() >= 20
        }
    m["groups"] = groups
    return m
