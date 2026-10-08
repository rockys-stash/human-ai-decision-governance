"""Experiment configs and runners (E1 calibration, E2 regimes, E3 frontier, E4 sensitivity,
E5 shift). Each run writes ``results/<experiment>/<UTC>-<commit7>/`` with the resolved config,
per-seed records (JSONL) and an aggregated ``summary.json`` carrying provenance."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from pydantic import BaseModel, Field

from governance.confidence.calibration import brier, ece, mce, nll, reliability_bins
from governance.data.domains import DOMAINS, make_synthetic
from governance.experiments.stats import aggregate, paired_test
from governance.experiments.stream import Stream, build_stream, seed_for
from governance.humans.reviewer import Mode, ReviewerModel, Staffing
from governance.policy.policy import Policy
from governance.regimes.regimes import (
    REGIMES,
    ROUTERS,
    modes_for_regime,
    outcome_metrics,
    routing_scores,
    run_modes,
)

Kind = Literal["calibration", "regimes", "frontier", "sensitivity", "shift"]


class SweepAxis(BaseModel):
    param: str  # a ReviewerModel or Staffing field
    values: list[float]


class ExperimentConfig(BaseModel):
    experiment: str = Field(pattern=r"^[a-z0-9_]+$")
    description: str
    kind: Kind
    base_seed: int
    seeds: int = Field(ge=1)
    domains: list[str] = list(DOMAINS)
    model: str = "gbm"
    calibrator: str = "isotonic"
    models: list[str] = ["gbm", "logreg"]  # calibration experiment
    calibrators: list[str] = ["none", "platt", "isotonic"]
    reviewer: ReviewerModel = ReviewerModel()
    staffing: Staffing = Staffing()
    policies: dict[str, str] = {d: f"configs/policies/{d}.yaml" for d in DOMAINS}
    frontier_shares: list[float] = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0]
    frontier_mode: Literal["review", "approval"] = "review"
    matched_share: float = 0.2
    sweeps: list[SweepAxis] = []
    shift_levels: list[float] = [0.0, 0.5, 1.0]


def load_config(path: Path) -> ExperimentConfig:
    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text()))


def _commit(root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _seeds(cfg: ExperimentConfig) -> list[int]:
    return [cfg.base_seed + i for i in range(cfg.seeds)]


def _policies(cfg: ExperimentConfig, root: Path) -> dict[str, Policy]:
    return {d: Policy.load(root / p) for d, p in cfg.policies.items() if d in cfg.domains}


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating | float):
        f = float(x)
        return f if np.isfinite(f) else None
    return x


# --- E1 calibration ---------------------------------------------------------------------------
def run_calibration(
    cfg: ExperimentConfig, root: Path, log: Callable[[str], None]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    pooled: dict[str, dict[str, list[np.ndarray]]] = {}
    for domain in cfg.domains:
        for seed in _seeds(cfg):
            for model in cfg.models:
                for cal in cfg.calibrators:
                    st = build_stream(domain, seed, cfg.reviewer, cfg.staffing, model, cal)
                    out, y = st.ctx.out, st.ctx.y
                    correct = (out.decision == y).astype(float)
                    rec = {
                        "domain": domain, "seed": seed, "model": model, "calibrator": cal,
                        "n_test": len(y), "accuracy": float(correct.mean()),
                        "ece": ece(out.confidence, correct), "mce": mce(out.confidence, correct),
                        "brier": brier(out.p, y), "nll": nll(out.p, y),
                        "mean_confidence": float(out.confidence.mean()),
                    }  # fmt: skip
                    if st.ctx.domain.true_p is not None:
                        tp = st.ctx.domain.true_p[out.idx]
                        rec["mae_true_p"] = float(np.abs(out.p - tp).mean())
                        rec["brier_true_p"] = brier(tp, y)  # irreducible (Bayes) Brier score
                    records.append(rec)
                    key = f"{domain}|{model}|{cal}"
                    pooled.setdefault(key, {"conf": [], "correct": []})
                    pooled[key]["conf"].append(out.confidence)
                    pooled[key]["correct"].append(correct)
            log(f"  {domain} seed {seed} done")
    diagrams = {
        k: reliability_bins(np.concatenate(v["conf"]), np.concatenate(v["correct"]), 15)
        for k, v in pooled.items()
    }
    metrics = [
        "accuracy",
        "ece",
        "mce",
        "brier",
        "nll",
        "mean_confidence",
        "mae_true_p",
        "brier_true_p",
    ]
    summary: dict[str, Any] = {"by_condition": {}, "reliability": diagrams, "pairwise": []}
    for domain in cfg.domains:
        for model in cfg.models:
            for cal in cfg.calibrators:
                rs = [
                    r
                    for r in records
                    if (r["domain"], r["model"], r["calibrator"]) == (domain, model, cal)
                ]
                summary["by_condition"][f"{domain}|{model}|{cal}"] = {
                    m: aggregate([r[m] for r in rs]) for m in metrics if m in rs[0]
                }
            # Does calibration help? Paired over seeds, against the uncalibrated model.
            base = sorted(
                (
                    r
                    for r in records
                    if (r["domain"], r["model"], r["calibrator"]) == (domain, model, "none")
                ),
                key=lambda r: r["seed"],
            )
            for cal in cfg.calibrators:
                if cal == "none":
                    continue
                other = sorted(
                    (
                        r
                        for r in records
                        if (r["domain"], r["model"], r["calibrator"]) == (domain, model, cal)
                    ),
                    key=lambda r: r["seed"],
                )
                for metric in ("ece", "brier"):
                    summary["pairwise"].append({
                        "domain": domain, "model": model, "metric": metric, "a": cal, "b": "none",
                        **paired_test([r[metric] for r in other], [r[metric] for r in base]),
                    })  # fmt: skip
    return records, summary


# --- E2 regimes -------------------------------------------------------------------------------
def _regime_records(
    st: Stream, policy: Policy, domain: str, seed: int, extra: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    recs = []
    for regime in REGIMES:
        modes, routing = modes_for_regime(regime, st.ctx, policy)
        res = run_modes(st.ctx, modes)
        m = outcome_metrics(st.ctx, modes, res, routing)
        recs.append({"domain": domain, "seed": seed, "regime": regime, **(extra or {}), **m})
    return recs


SCALAR_REGIME_METRICS = (
    "accuracy", "error_rate", "loss_per_1000", "share_human", "reviewer_hours_per_1000",
    "decision_minutes_median", "decision_minutes_p95", "human_decision_minutes_median",
    "utilisation", "override_rate", "override_precision", "automation_bias_rate",
    "appropriate_reliance", "high_stake_errors_per_1000",
)  # fmt: skip


def _summarise_regimes(
    records: list[dict[str, Any]],
    domains: Iterable[str],
    key: Callable[[dict[str, Any]], Any] = lambda r: None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for domain in domains:
        rs = [r for r in records if r["domain"] == domain]
        by: dict[str, Any] = {}
        for regime in REGIMES:
            rr = [r for r in rs if r["regime"] == regime]
            by[regime] = {m: aggregate([r.get(m) for r in rr]) for m in SCALAR_REGIME_METRICS}
            by[regime]["errors"] = {
                k: aggregate([r["errors"][k] / r["n"] * 1000 for r in rr]) for k in rr[0]["errors"]
            }
            if "tier_share" in rr[0]:
                by[regime]["tier_share"] = {
                    k: aggregate([r["tier_share"][k] for r in rr]) for k in rr[0]["tier_share"]
                }
                by[regime]["error_by_tier"] = {
                    k: aggregate([r["error_by_tier"][k] for r in rr])
                    for k in rr[0]["error_by_tier"]
                }
                fired: dict[str, float] = {}
                for r in rr:
                    for k, v in r["rules_fired"].items():
                        fired[k] = fired.get(k, 0) + v / r["n"] / len(rr)
                by[regime]["rules_fired_share"] = fired
            groups: dict[str, Any] = {}
            for g, vals in rr[0]["groups"].items():
                groups[g] = {
                    lv: {
                        "error_rate": aggregate(
                            [r["groups"][g][lv]["error_rate"] for r in rr if lv in r["groups"][g]]
                        ),
                        "share_human": aggregate(
                            [r["groups"][g][lv]["share_human"] for r in rr if lv in r["groups"][g]]
                        ),
                    }
                    for lv in vals
                }
            by[regime]["groups"] = groups
        pairs = []
        for i, a in enumerate(REGIMES):
            for b in REGIMES[i + 1 :]:
                for metric in ("loss_per_1000", "accuracy", "reviewer_hours_per_1000"):
                    ra = sorted((r for r in rs if r["regime"] == a), key=lambda r: r["seed"])
                    rb = sorted((r for r in rs if r["regime"] == b), key=lambda r: r["seed"])
                    pairs.append(
                        {
                            "metric": metric,
                            "a": a,
                            "b": b,
                            **paired_test([r[metric] for r in ra], [r[metric] for r in rb]),
                        }
                    )
        out[domain] = {"regimes": by, "pairwise": _holm(pairs)}
    return out


def _holm(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from governance.experiments.stats import holm

    for metric in {p["metric"] for p in pairs}:
        ps = [p for p in pairs if p["metric"] == metric]
        for p, adj in zip(ps, holm([p["p_value"] for p in ps]), strict=True):
            p["p_holm"] = adj
    return pairs


def run_regimes(
    cfg: ExperimentConfig, root: Path, log: Callable[[str], None]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policies = _policies(cfg, root)
    records: list[dict[str, Any]] = []
    for domain in cfg.domains:
        for seed in _seeds(cfg):
            st = build_stream(domain, seed, cfg.reviewer, cfg.staffing, cfg.model, cfg.calibrator)
            records += _regime_records(st, policies[domain], domain, seed)
        log(f"  {domain}: {cfg.seeds} seeds")
    summary = {
        "domains": _summarise_regimes(records, cfg.domains),
        "policies": {
            d: {"id": p.id, "version": p.version, "hash": p.hash, **p.model_dump()}
            for d, p in policies.items()
        },
    }
    return records, summary


# --- E3 frontier and routing ablations --------------------------------------------------------
def run_frontier(
    cfg: ExperimentConfig, root: Path, log: Callable[[str], None]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policies = _policies(cfg, root)
    records: list[dict[str, Any]] = []
    for domain in cfg.domains:
        for seed in _seeds(cfg):
            st = build_stream(domain, seed, cfg.reviewer, cfg.staffing, cfg.model, cfg.calibrator)
            rng = np.random.default_rng(seed_for(seed, domain, "random-router"))
            for router in ROUTERS:
                uncal = router == "expected_cost_uncalibrated"
                base = "expected_cost" if uncal else router
                calib_out = st.calib_out_uncal if uncal else st.calib_out
                stream_out = st.ctx.out_uncal if uncal else st.ctx.out
                s_cal = routing_scores(base, st.ctx, calib_out, rng)
                s_stream = routing_scores(base, st.ctx, stream_out, rng)
                # Break ties at random so a constant score (unit stakes in eligibility) selects the
                # target share instead of everyone or no one. Jitter is far below any real gap.
                s_cal = s_cal + rng.uniform(0, 1e-9, len(s_cal))
                s_stream = s_stream + rng.uniform(0, 1e-9, len(s_stream))
                for q in cfg.frontier_shares:
                    if q <= 0:
                        human = np.zeros(len(s_stream), dtype=bool)
                    elif q >= 1:
                        human = np.ones(len(s_stream), dtype=bool)
                    elif router == "random":
                        human = s_stream >= 1 - q
                    else:
                        # Threshold from the calibration split: no peeking at the test stream.
                        human = s_stream >= np.quantile(s_cal, 1 - q)
                    modes: list[Mode | None] = [cfg.frontier_mode if h else None for h in human]
                    res = run_modes(st.ctx, modes)
                    m = outcome_metrics(st.ctx, modes, res)
                    records.append({
                        "domain": domain, "seed": seed, "router": router, "target_share": q,
                        **{k: m[k] for k in ("loss_per_1000", "accuracy", "share_human", "reviewer_hours_per_1000", "high_stake_errors_per_1000") if k in m},
                    })  # fmt: skip
            # The configured two-tier policy, for reference on the same axes.
            modes, routing = modes_for_regime("risk_adaptive", st.ctx, policies[domain])
            m = outcome_metrics(st.ctx, modes, run_modes(st.ctx, modes), routing)
            records.append({"domain": domain, "seed": seed, "router": "policy", "target_share": None,
                            **{k: m[k] for k in ("loss_per_1000", "accuracy", "share_human", "reviewer_hours_per_1000", "high_stake_errors_per_1000") if k in m}})  # fmt: skip
        log(f"  {domain}: {cfg.seeds} seeds")
    summary: dict[str, Any] = {
        "domains": {},
        "matched_share": cfg.matched_share,
        "mode": cfg.frontier_mode,
    }
    for domain in cfg.domains:
        rs = [r for r in records if r["domain"] == domain]
        curves: dict[str, list[dict[str, Any]]] = {}
        for router in ROUTERS:
            curves[router] = [
                {"target_share": q, **{k: aggregate([r.get(k) for r in rs if r["router"] == router and r["target_share"] == q])
                                       for k in ("loss_per_1000", "accuracy", "share_human", "reviewer_hours_per_1000", "high_stake_errors_per_1000")}}
                for q in cfg.frontier_shares
            ]  # fmt: skip
        pol = [r for r in rs if r["router"] == "policy"]
        policy_point = {
            k: aggregate([r.get(k) for r in pol])
            for k in (
                "loss_per_1000",
                "accuracy",
                "share_human",
                "reviewer_hours_per_1000",
                "high_stake_errors_per_1000",
            )
        }
        matched = []
        q = cfg.matched_share
        ec = sorted(
            (r for r in rs if r["router"] == "expected_cost" and r["target_share"] == q),
            key=lambda r: r["seed"],
        )
        for router in ROUTERS[1:]:
            other = sorted(
                (r for r in rs if r["router"] == router and r["target_share"] == q),
                key=lambda r: r["seed"],
            )
            matched.append(
                {
                    "metric": "loss_per_1000",
                    "a": "expected_cost",
                    "b": router,
                    **paired_test(
                        [r["loss_per_1000"] for r in ec], [r["loss_per_1000"] for r in other]
                    ),
                }
            )
        summary["domains"][domain] = {
            "curves": curves,
            "policy": policy_point,
            "matched": _holm(matched),
        }
    return records, summary


# --- E4 sensitivity ---------------------------------------------------------------------------
def run_sensitivity(
    cfg: ExperimentConfig, root: Path, log: Callable[[str], None]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policies = _policies(cfg, root)
    records: list[dict[str, Any]] = []
    for axis in cfg.sweeps:
        for value in axis.values:
            reviewer, staffing = cfg.reviewer, cfg.staffing
            if axis.param in ReviewerModel.model_fields:
                reviewer = reviewer.model_copy(update={axis.param: value})
            elif axis.param in Staffing.model_fields:
                staffing = staffing.model_copy(
                    update={axis.param: int(value) if axis.param == "reviewers" else value}
                )
            else:
                raise ValueError(f"unknown sweep parameter '{axis.param}'")
            for domain in cfg.domains:
                for seed in _seeds(cfg):
                    st = build_stream(domain, seed, reviewer, staffing, cfg.model, cfg.calibrator)
                    for r in _regime_records(
                        st, policies[domain], domain, seed, {"param": axis.param, "value": value}
                    ):
                        records.append(
                            {
                                k: r[k]
                                for k in (
                                    "domain",
                                    "seed",
                                    "regime",
                                    "param",
                                    "value",
                                    *SCALAR_REGIME_METRICS,
                                )
                                if k in r
                            }
                        )
            log(f"  {axis.param} = {value}")
    summary: dict[str, Any] = {"axes": {}}
    for axis in cfg.sweeps:
        per_domain: dict[str, Any] = {}
        for domain in cfg.domains:
            rows = []
            for value in axis.values:
                rs = [
                    r
                    for r in records
                    if r["param"] == axis.param and r["value"] == value and r["domain"] == domain
                ]
                row: dict[str, Any] = {"value": value}
                for regime in REGIMES:
                    rr = [r for r in rs if r["regime"] == regime]
                    row[regime] = {
                        m: aggregate([r.get(m) for r in rr])
                        for m in (
                            "loss_per_1000",
                            "accuracy",
                            "reviewer_hours_per_1000",
                            "decision_minutes_p95",
                        )
                    }
                best = min(REGIMES, key=lambda g: row[g]["loss_per_1000"]["mean"])
                row["lowest_loss_regime"] = best
                ra = sorted(
                    (r for r in rs if r["regime"] == "risk_adaptive"), key=lambda r: r["seed"]
                )
                for other in ("ai_only", "blanket_approval", "human_only"):
                    rb = sorted((r for r in rs if r["regime"] == other), key=lambda r: r["seed"])
                    row[f"adaptive_vs_{other}"] = paired_test(
                        [r["loss_per_1000"] for r in ra], [r["loss_per_1000"] for r in rb]
                    )
                rows.append(row)
            per_domain[domain] = rows
        summary["axes"][axis.param] = per_domain
    return records, summary


# --- E5 distribution shift (synthetic domain) --------------------------------------------------
def run_shift(
    cfg: ExperimentConfig, root: Path, log: Callable[[str], None]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policy = _policies(cfg.model_copy(update={"domains": ["payments"]}), root)["payments"]
    records: list[dict[str, Any]] = []
    for kind in ("covariate", "concept"):
        for level in cfg.shift_levels:
            for seed in _seeds(cfg):
                gen_seed = seed_for(seed, "payments-data")
                train_domain = make_synthetic(seed=gen_seed)
                shifted = make_synthetic(
                    seed=seed_for(seed, "payments-shifted", kind, level),
                    covariate_shift=level if kind == "covariate" else 0.0,
                    concept_shift=level if kind == "concept" else 0.0,
                )
                st = build_stream(
                    train_domain,
                    seed,
                    cfg.reviewer,
                    cfg.staffing,
                    cfg.model,
                    cfg.calibrator,
                    test_domain=shifted,
                )
                out, y = st.ctx.out, st.ctx.y
                correct = (out.decision == y).astype(float)
                cal = {"ece": ece(out.confidence, correct), "brier": brier(out.p, y), "ai_accuracy": float(correct.mean()),
                       "mean_confidence": float(out.confidence.mean())}  # fmt: skip
                for r in _regime_records(
                    st, policy, "payments", seed, {"shift": kind, "level": level}
                ):
                    records.append({**{k: r[k] for k in ("domain", "seed", "regime", "shift", "level", *SCALAR_REGIME_METRICS) if k in r},
                                    **cal, "tier_share": r.get("tier_share")})  # fmt: skip
            log(f"  {kind} shift {level}")
    summary: dict[str, Any] = {"shifts": {}}
    for kind in ("covariate", "concept"):
        rows = []
        for level in cfg.shift_levels:
            rs = [r for r in records if r["shift"] == kind and r["level"] == level]
            row: dict[str, Any] = {"level": level}
            ai = [r for r in rs if r["regime"] == "ai_only"]
            for m in ("ece", "brier", "ai_accuracy", "mean_confidence"):
                row[m] = aggregate([r[m] for r in ai])
            for regime in REGIMES:
                rr = [r for r in rs if r["regime"] == regime]
                row[regime] = {
                    m: aggregate([r.get(m) for r in rr])
                    for m in ("loss_per_1000", "accuracy", "reviewer_hours_per_1000", "share_human")
                }
            adaptive = [r for r in rs if r["regime"] == "risk_adaptive"]
            row["autonomous_share"] = aggregate([r["tier_share"]["autonomous"] for r in adaptive])
            rows.append(row)
        summary["shifts"][kind] = rows
    return records, summary


RUNNERS: dict[
    str,
    Callable[
        [ExperimentConfig, Path, Callable[[str], None]], tuple[list[dict[str, Any]], dict[str, Any]]
    ],
] = {
    "calibration": run_calibration,
    "regimes": run_regimes,
    "frontier": run_frontier,
    "sensitivity": run_sensitivity,
    "shift": run_shift,
}


def run_experiment(cfg_path: Path, root: Path, quiet: bool = False) -> Path:
    cfg = load_config(cfg_path)
    log: Callable[[str], None] = (lambda s: None) if quiet else (lambda s: print(s, flush=True))
    commit = _commit(root)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = root / "results" / cfg.experiment / f"{stamp}-{commit[:7]}"
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "config.yaml").write_text(yaml.safe_dump(cfg.model_dump(), sort_keys=False))
    log(f"{cfg.experiment}: {cfg.description}")
    t0 = time.time()
    records, summary = RUNNERS[cfg.kind](cfg, root, log)
    with (out_dir / "records.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(_jsonable(r), allow_nan=False) + "\n")
    summary["provenance"] = {
        "experiment": cfg.experiment, "description": cfg.description, "kind": cfg.kind,
        "run_id": out_dir.name, "created_at": stamp, "commit": commit,
        "base_seed": cfg.base_seed, "seeds": cfg.seeds, "domains": cfg.domains,
        "model": cfg.model, "calibrator": cfg.calibrator,
        "reviewer": cfg.reviewer.model_dump(), "staffing": cfg.staffing.model_dump(),
        "python": platform.python_version(), "runtime_seconds": round(time.time() - t0, 1),
    }  # fmt: skip
    (out_dir / "summary.json").write_text(json.dumps(_jsonable(summary), indent=1, allow_nan=False))
    (root / "results" / cfg.experiment / "LATEST").write_text(out_dir.name + "\n")
    log(f"wrote {out_dir.relative_to(root)} in {time.time() - t0:.0f}s")
    return out_dir
