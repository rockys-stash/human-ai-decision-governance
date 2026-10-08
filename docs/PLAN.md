# Plan — Human-in-the-Loop Decision Governance Framework

## 1. Scope

A framework that decides, case by case, whether an AI agent's decision is executed autonomously, sent to a human for review, or held for mandatory human approval:

```
Case ─► AI agent (decision + raw score) ─► Confidence estimator (calibrated) ─► Risk assessment (expected cost + policy rules)
     ─► Router:  low risk → autonomous   ·   medium → human review   ·   high → mandatory approval  ─► Outcome + audit record
```

In scope:

1. **Workflow simulator** producing a stream of decision cases of graded risk (arrival times, stakes, policy attributes, ground-truth outcome), over three domains (§5).
2. **AI agent**: a trained classifier making the case decision.
3. **Confidence estimator** with measured calibration (uncalibrated, Platt scaling, isotonic regression), fitted on a calibration split disjoint from training and test.
4. **Risk assessment and routing** under configurable, version-hashed YAML policies: expected-cost thresholds plus hard rules. Every routing decision writes an audit record (scores, thresholds, rules fired, policy hash).
5. **Simulated reviewer model** (explicitly a model, not people): unaided accuracy that depends on case difficulty, detection of AI errors vs. automation bias, fatigue, handling time and finite reviewer capacity with queueing.
6. **Experiment harness** comparing the four oversight regimes required by the spec: human-only, AI-only, AI + blanket approval, risk-adaptive oversight, with ablations, threshold sweeps, sensitivity analysis and distribution shift.
7. **Decision console UI** with a live human review queue (real reviewer actions are recorded), policy view, experiment results, calibration and audit log.

Out of scope: claims about real human behaviour. Human trust is measured only by proxy (appropriate reliance in simulation); a real user study is *Status: pending* (§8), with the review queue built to serve as its instrument.

## 2. Research questions and hypotheses

- **RQ1 — Calibration.** How well do the agent's confidence scores match observed accuracy, before and after post-hoc calibration, per domain and under distribution shift?
  *H1:* post-hoc calibration lowers expected calibration error (ECE) on held-out data; calibration degrades under shift.
- **RQ2 — Regimes.** How do the four regimes trade off cost-weighted error, accuracy, decision time and human workload?
  *H2:* risk-adaptive oversight reaches cost-weighted loss within the confidence interval of blanket approval while using a fraction of its reviewer hours; AI-only has the highest high-stakes loss; human-only is slowest.
- **RQ3 — What makes routing work.** Does routing need calibrated confidence and stakes, or would a simpler rule do as well?
  *H3:* at equal human workload, risk-adaptive routing beats random audit; routing on expected cost (confidence × stake) beats confidence-only and stake-only routing; uncalibrated confidence degrades routing.
- **RQ4 — Robustness.** Under which reviewer-model parameters (automation bias, unaided accuracy, capacity) and data shifts does risk-adaptive oversight lose its advantage?

Baselines: AI-only (no oversight), human-only (no AI), blanket approval (maximal oversight), and **random audit at matched workload** (the defensible baseline for any routing policy).

## 3. Architecture

```
src/governance/
  data/        dataset loaders (German Credit, Adult), synthetic domain generator, splits, preprocessing
  agent/       classifier wrapper (fit on train split only)
  confidence/  calibrators (none / Platt / isotonic), calibration metrics (ECE, MCE, Brier, NLL, reliability bins)
  policy/      YAML policy schema, expected-cost risk score, hard rules, router, audit records (policy hash)
  humans/      simulated reviewer model + capacity/queue simulation (arrival clock, staffed queue)
  regimes/     the four regimes and ablation routers
  experiments/ per-seed stream builder (split, agent, calibration, difficulty), runner, statistics, report generator, CLI
  api/         FastAPI: results (read-only) + live review queue (token-protected writes, SQLite)
web/           React + TypeScript decision console
```

Core logic is independent of the API and UI; the simulator is deterministic given a seed.

## 4. Technology

Python 3.11+ (tested 3.13), NumPy, scikit-learn (models, calibrators), pydantic v2, PyYAML, FastAPI, SQLite (stdlib). React 18 + TypeScript strict + Vite; hand-built SVG charts. pytest, Playwright, ruff, mypy (strict), ESLint. uv and npm lockfiles.

## 5. Data

| Domain | Source | License | Rows | Decision | Stake |
|---|---|---|---|---|---|
| Credit approval | UCI Statlog (German Credit) | CC BY 4.0 | 1,000 | approve / decline loan | credit amount (DM) |
| Eligibility screening | UCI Adult (Census Income) | CC BY 4.0 | 48,842 | eligible / not eligible for an income-tested programme (income ≤ 50K) | unit stakes with asymmetric costs (false denial 3, false grant 1) |
| Operations approvals | Synthetic (this repo) | MIT | configurable | approve / reject a payment | amount (log-normal) |

The synthetic domain has a known generative model, so true outcome probabilities are available and calibration can be checked against ground truth, and shift can be injected in controlled amounts. Raw files are committed with SHA-256 pins and attribution (`data/DATASET.md`). Splits per seed: train 60% / calibration 20% / test stream 20%, stratified; preprocessing fitted on train only; leakage checks are unit-tested (disjoint row ids, no test statistics used before evaluation).

Framing caveat: Adult's label is income above 50K in 1994 census data; the "eligibility" framing is a stand-in for an income-tested screening decision, not a claim about a real programme. The dataset has documented demographic biases; error rates and routing rates are reported by sex and race group as part of error analysis.

## 6. Experiments

All runs: YAML config in `configs/`, logged seed, outputs in `results/<experiment>/<timestamp>-<commit>/`, one-command reproduction (`scripts/reproduce.sh`).

| ID | Question | Design | Seeds |
|---|---|---|---|
| E1 | RQ1 | Calibrators × domains: ECE, MCE, Brier, NLL, reliability diagrams; synthetic domain also vs. true probabilities | 20 |
| E2 | RQ2 | Four regimes × three domains, default policy and reviewer model | 20 |
| E3 | RQ3 | Threshold sweep → workload / loss frontier; random audit, confidence-only, stake-only, uncalibrated routing at matched workload | 20 |
| E4 | RQ4 | Sensitivity: automation bias in review, hard-case accuracy, review time, reviewer capacity | 10 per point |
| E5 | RQ1, RQ4 | Synthetic domain with covariate and concept shift in the test stream | 20 |

Error analysis: every incorrect final decision is attributed to one cause — autonomous AI error, automation-bias acceptance (reviewer accepted a wrong AI decision), harmful override (reviewer overturned a correct AI decision), or unaided human error — broken down by tier and domain, plus group-wise error and routing rates on Adult and German Credit.

## 7. Metrics

Accuracy; error rate; cost-weighted loss (per 1,000 cases); high-stakes errors; decision time (median and 95th percentile, including queue wait); human workload (reviewer-hours, share of cases touched); override rate and override precision; automation-bias rate; calibration (ECE with equal-mass bins, MCE, Brier, NLL); appropriate reliance (share of reviewer actions that accept correct and override incorrect AI decisions) as the trust proxy. Statistics: mean ± std over seeds, 95% percentile intervals over seeds, paired comparisons between regimes on the same seed (sign-flip permutation test, Holm correction).

## 8. Risks and external dependencies

| Dependency | Status | Mitigation |
|---|---|---|
| Human participants (trust, real reviewer behaviour) | **Unavailable** | Parametric reviewer model with sensitivity analysis; trust reported only as a proxy; the review queue records real reviewer actions and can serve as the study instrument (*Status: pending human study*) |
| Empirical reviewer parameters | Not measured here | Defaults are illustrative round values, stated as assumptions; conclusions are tested across parameter ranges (E4) rather than at one point |
| Datasets | Available (UCI via GitHub mirror, verified by row count and checksum) | Files committed with checksums |
| LLM-based agent | Not needed | The agent is a classifier: governance logic is agent-agnostic and takes any (decision, score) source |

Risk: a simulation can only show consequences of its assumptions. The report separates findings that hold across the sensitivity ranges from those that depend on specific parameter values.

Implementation deviations from this plan are recorded in `docs/DECISIONS.md` (D18).
