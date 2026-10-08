"""Simulated human reviewers and the review queue.

This is a *model* of reviewers, not data about people. Every parameter is an explicit assumption
listed in the experiment config and varied in the sensitivity experiment (E4).

Decision procedure for one case, given difficulty ``d`` in [0, 1] (1 = maximally ambiguous):

1. The reviewer forms an independent judgement that is correct with probability
   ``acc(d) = acc_easy - (acc_easy - acc_hard) * d - fatigue - mode_penalty``.
2. ``unaided`` (no AI shown): the judgement is the decision.
3. ``review`` / ``approval`` (AI decision shown): if the judgement agrees with the AI, the AI decision
   is accepted. If it disagrees, the reviewer defers to the AI with probability ``automation_bias``
   for that mode, otherwise overrides it with their own judgement.

Handling time is log-normal around a per-mode mean, longer for harder cases. Cases wait in a queue
served by a fixed number of reviewers; approvals are served before reviews (non-preemptive).
Fatigue grows with continuous busy time and resets after an idle gap.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

Mode = Literal["unaided", "review", "approval"]
MODES: tuple[Mode, ...] = ("unaided", "review", "approval")


class ReviewerModel(BaseModel):
    acc_easy: float = Field(0.95, ge=0.5, le=1.0)
    acc_hard: float = Field(0.65, ge=0.0, le=1.0)
    review_accuracy_penalty: float = Field(0.05, ge=0.0, le=0.5)
    automation_bias_review: float = Field(0.5, ge=0.0, le=1.0)
    automation_bias_approval: float = Field(0.2, ge=0.0, le=1.0)
    minutes_unaided: float = Field(6.0, gt=0)
    minutes_review: float = Field(2.0, gt=0)
    minutes_approval: float = Field(6.0, gt=0)
    time_sigma: float = Field(0.5, ge=0)
    difficulty_time_factor: float = Field(0.5, ge=0)
    fatigue_per_busy_hour: float = Field(0.01, ge=0)
    fatigue_cap: float = Field(0.05, ge=0)
    fatigue_reset_idle_minutes: float = Field(15.0, ge=0)


class Staffing(BaseModel):
    reviewers: int = Field(4, ge=1)
    arrivals_per_hour: float = Field(30.0, gt=0)


@dataclass
class CaseDraws:
    """Common random numbers for a case stream, shared by every regime on the same seed so that
    regime comparisons are paired."""

    judge: np.ndarray
    defer: np.ndarray
    time_z: np.ndarray
    arrival_min: np.ndarray

    @classmethod
    def draw(cls, n: int, rng: np.random.Generator, arrivals_per_hour: float) -> CaseDraws:
        gaps = rng.exponential(60.0 / arrivals_per_hour, n)
        return cls(rng.random(n), rng.random(n), rng.standard_normal(n), np.cumsum(gaps))


@dataclass
class HumanResult:
    decision: np.ndarray
    action: (
        np.ndarray
    )  # "", "unaided", "accept", "override", "defer" (accepted despite disagreeing)
    start_min: np.ndarray
    end_min: np.ndarray
    handling_min: np.ndarray
    reviewer: np.ndarray
    fatigue: np.ndarray
    queue_peak: int = 0
    utilisation: float = 0.0
    log: list[str] = field(default_factory=list)


def handling_minutes(m: ReviewerModel, mode: Mode, d: float, z: float) -> float:
    mean = {
        "unaided": m.minutes_unaided,
        "review": m.minutes_review,
        "approval": m.minutes_approval,
    }[mode]
    mean *= 1.0 + m.difficulty_time_factor * d
    # Log-normal with the given mean: mu = ln(mean) - sigma^2 / 2.
    return float(np.exp(np.log(mean) - m.time_sigma**2 / 2 + m.time_sigma * z))


def judge(
    m: ReviewerModel,
    mode: Mode,
    y: int,
    ai: int,
    d: float,
    fatigue: float,
    u_judge: float,
    u_defer: float,
) -> tuple[int, str]:
    acc = m.acc_easy - (m.acc_easy - m.acc_hard) * d - fatigue
    if mode == "review":
        acc -= m.review_accuracy_penalty
    acc = float(np.clip(acc, 0.0, 1.0))
    own = y if u_judge < acc else 1 - y
    if mode == "unaided":
        return own, "unaided"
    if own == ai:
        return ai, "accept"
    bias = m.automation_bias_review if mode == "review" else m.automation_bias_approval
    if u_defer < bias:
        return ai, "defer"
    return own, "override"


def simulate_queue(
    model: ReviewerModel,
    staffing: Staffing,
    modes: list[Mode | None],
    y: np.ndarray,
    ai: np.ndarray,
    difficulty: np.ndarray,
    draws: CaseDraws,
) -> HumanResult:
    """Serve the cases that need a human (``modes[j]`` not None) with a fixed reviewer pool.

    Approvals are served before reviews and unaided decisions; within a class, first come first
    served. Cases with ``modes[j] is None`` are decided by the AI at arrival.
    """
    n = len(y)
    decision = ai.astype(int).copy()
    action = np.array([""] * n, dtype=object)
    start = draws.arrival_min.copy()
    end = draws.arrival_min.copy()
    handling = np.zeros(n)
    who = np.full(n, -1)
    fat = np.zeros(n)

    priority = {"approval": 0, "unaided": 1, "review": 1}
    free_at = [0.0] * staffing.reviewers
    busy_since = [0.0] * staffing.reviewers
    waiting: list[tuple[int, float, int]] = []  # (priority, arrival, case)
    human_cases = [j for j in range(n) if modes[j] is not None]
    k = 0
    peak = 0
    busy_total = 0.0
    while k < len(human_cases) or waiting:
        # Earliest time a reviewer is free.
        r = min(range(staffing.reviewers), key=lambda i: free_at[i])
        t_free = free_at[r]
        # Admit every arrival up to the moment that reviewer can start (or the next arrival if idle).
        if not waiting and k < len(human_cases):
            t_free = max(t_free, draws.arrival_min[human_cases[k]])
        while k < len(human_cases) and draws.arrival_min[human_cases[k]] <= t_free:
            j = human_cases[k]
            mode = modes[j]
            assert mode is not None
            heapq.heappush(waiting, (priority[mode], float(draws.arrival_min[j]), j))
            k += 1
        peak = max(peak, len(waiting))
        _, arr, j = heapq.heappop(waiting)
        mode = modes[j]
        assert mode is not None
        t0 = max(t_free, arr)
        if t0 - free_at[r] >= model.fatigue_reset_idle_minutes:
            busy_since[r] = t0
        fatigue = min(model.fatigue_cap, model.fatigue_per_busy_hour * (t0 - busy_since[r]) / 60.0)
        dec, act = judge(
            model, mode, int(y[j]), int(ai[j]), float(difficulty[j]), fatigue,
            float(draws.judge[j]), float(draws.defer[j]),
        )  # fmt: skip
        h = handling_minutes(model, mode, float(difficulty[j]), float(draws.time_z[j]))
        decision[j], action[j], start[j], end[j], handling[j], who[j], fat[j] = (
            dec, act, t0, t0 + h, h, r, fatigue,
        )  # fmt: skip
        free_at[r] = t0 + h
        busy_total += h
    horizon = float(max(end.max(), draws.arrival_min.max())) if n else 0.0
    util = busy_total / (staffing.reviewers * horizon) if horizon > 0 else 0.0
    return HumanResult(decision, action, start, end, handling, who, fat, peak, util)
