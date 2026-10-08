"""Risk policies and routing.

A policy is a YAML document: two expected-cost thresholds that grade the risk of executing the AI
decision, plus hard rules that can raise (never lower) a case's tier. The policy's content hash is
written into every routing record so any decision can be traced to the exact policy that routed it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from pydantic import BaseModel, Field, model_validator

from governance.agent.model import AgentOutput
from governance.data.domains import Domain

Tier = Literal["autonomous", "review", "approval"]
TIERS: tuple[Tier, ...] = ("autonomous", "review", "approval")
TIER_RANK = {t: i for i, t in enumerate(TIERS)}

Op = Literal["gt", "gte", "lt", "lte", "eq", "in"]


class Condition(BaseModel):
    """``field`` is one of stake, confidence, expected_cost, p, decision (1 = positive action), or
    ``feature:<name>``."""

    field: str = Field(pattern=r"^(stake|confidence|expected_cost|p|decision|feature:[a-z_]+)$")
    op: Op
    value: float | str | list[str] | list[float]


class Rule(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    description: str
    route: Literal["review", "approval"]
    when: list[Condition] = Field(min_length=1)  # all conditions must hold


class Thresholds(BaseModel):
    review: float = Field(ge=0)
    approval: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> Thresholds:
        if self.approval < self.review:
            raise ValueError("approval threshold must be >= review threshold")
        return self


class Policy(BaseModel):
    id: str
    version: str
    domain: str
    description: str
    thresholds: Thresholds
    rules: list[Rule] = []

    @property
    def hash(self) -> str:
        blob = json.dumps(self.model_dump(), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:12]

    @classmethod
    def load(cls, path: Path) -> Policy:
        return cls.model_validate(yaml.safe_load(path.read_text()))

    def with_thresholds(self, review: float, approval: float) -> Policy:
        return self.model_copy(update={"thresholds": Thresholds(review=review, approval=approval)})


@dataclass
class Routing:
    """Routing of a batch of cases (arrays aligned with the agent output)."""

    cost_tier: np.ndarray  # tier index from the expected-cost thresholds
    tier: np.ndarray  # final tier index after rules
    rules_fired: list[list[str]]


def _field(name: str, domain: Domain, out: AgentOutput) -> np.ndarray:
    if name == "stake":
        return domain.stake[out.idx]
    if name in {"confidence", "expected_cost", "p", "decision"}:
        return np.asarray(getattr(out, name))
    feat = name.split(":", 1)[1]
    return np.array([domain.features[i].get(feat) for i in out.idx], dtype=object)


def _same(a: Any, b: Any) -> bool:
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def _holds(c: Condition, values: np.ndarray) -> np.ndarray:
    v = c.value
    if c.op == "in":
        allowed = {str(x) for x in (v if isinstance(v, list) else [v])}
        return np.array([str(x) in allowed for x in values])
    if c.op == "eq":
        return np.array([_same(x, v) for x in values])
    num = np.asarray(values, dtype=float)
    ref = float(v)  # type: ignore[arg-type]
    return {"gt": num > ref, "gte": num >= ref, "lt": num < ref, "lte": num <= ref}[c.op]


def route(policy: Policy, domain: Domain, out: AgentOutput) -> Routing:
    ec = out.expected_cost
    cost_tier = np.where(
        ec >= policy.thresholds.approval, 2, np.where(ec >= policy.thresholds.review, 1, 0)
    )
    tier = cost_tier.copy()
    fired: list[list[str]] = [[] for _ in range(len(ec))]
    for rule in policy.rules:
        mask = np.ones(len(ec), dtype=bool)
        for c in rule.when:
            mask &= _holds(c, _field(c.field, domain, out))
        rank = TIER_RANK[rule.route]
        for i in np.flatnonzero(mask):
            fired[i].append(rule.id)
            tier[i] = max(tier[i], rank)
    return Routing(cost_tier=cost_tier, tier=tier, rules_fired=fired)


def audit_record(
    policy: Policy, domain: Domain, out: AgentOutput, routing: Routing, j: int, model_id: str
) -> dict[str, Any]:
    """Self-contained explanation of why case ``j`` of the batch was routed the way it was."""
    i = int(out.idx[j])
    return {
        "case_row": i,
        "policy_id": policy.id,
        "policy_version": policy.version,
        "policy_hash": policy.hash,
        "model": model_id,
        "p_raw": float(out.p_raw[j]),
        "p": float(out.p[j]),
        "ai_decision": domain.positive_action if out.decision[j] else domain.negative_action,
        "confidence": float(out.confidence[j]),
        "stake": float(domain.stake[i]),
        "expected_cost": float(out.expected_cost[j]),
        "thresholds": policy.thresholds.model_dump(),
        "cost_tier": TIERS[int(routing.cost_tier[j])],
        "rules_fired": routing.rules_fired[j],
        "tier": TIERS[int(routing.tier[j])],
    }
