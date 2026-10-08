"""Builds one seed's experimental stream: split, fitted agent, calibrated outputs, difficulty and
common random numbers. Shared by every experiment so all of them see identical cases per seed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from governance.agent.model import AgentOutput, DecisionAgent, reference_probability
from governance.data.domains import Domain, load_domain
from governance.data.prep import Split, stratified_split
from governance.humans.reviewer import CaseDraws, ReviewerModel, Staffing
from governance.regimes.regimes import StreamContext


@dataclass
class Stream:
    ctx: StreamContext
    split: Split
    agent: DecisionAgent
    calib_out: AgentOutput  # agent output on the calibration split (for threshold setting)
    calib_out_uncal: AgentOutput


def seed_for(base: int, *parts: Any) -> int:
    """Deterministic child seed (stable across Python runs, unlike hash())."""
    h = base
    for p in parts:
        for ch in str(p):
            h = (h * 1_000_003 + ord(ch)) % (2**32 - 1)
    return h


def build_stream(
    domain: Domain | str,
    seed: int,
    reviewer: ReviewerModel,
    staffing: Staffing,
    model: str = "gbm",
    calibrator: str = "isotonic",
    test_domain: Domain | None = None,
) -> Stream:
    """``test_domain``, when given, replaces the test stream's cases (same row count) to model
    distribution shift after deployment: the agent is trained and calibrated on ``domain``."""
    d = load_domain(domain) if isinstance(domain, str) else domain
    split = stratified_split(d.y, seed_for(seed, d.name, "split"))
    agent = DecisionAgent(d, model, calibrator, seed_for(seed, d.name, "model")).fit(split)
    calib_out = agent.predict(split.calib)
    calib_raw = agent.outputs(
        split.calib, calib_out.p_raw, np.clip(calib_out.p_raw, 1e-6, 1 - 1e-6)
    )

    stream_domain = d
    if test_domain is not None:
        stream_domain = test_domain
        agent.domain = test_domain  # predictions on shifted cases, same fitted model and encoder
    out = agent.predict(split.test)
    out_uncal = agent.outputs(split.test, out.p_raw, np.clip(out.p_raw, 1e-6, 1 - 1e-6))
    agent.domain = d

    p_ref = reference_probability(stream_domain, split, split.test, seed_for(seed, d.name, "ref"))
    difficulty = 1.0 - np.abs(2.0 * p_ref - 1.0)
    rng = np.random.default_rng(seed_for(seed, d.name, "humans"))
    draws = CaseDraws.draw(len(split.test), rng, staffing.arrivals_per_hour)
    train_stakes = d.stake[split.train]
    cut = float(np.percentile(train_stakes, 90)) if np.ptp(train_stakes) > 0 else None
    ctx = StreamContext(stream_domain, out, out_uncal, difficulty, draws, reviewer, staffing, cut)
    return Stream(ctx, split, agent, calib_out, calib_raw)
