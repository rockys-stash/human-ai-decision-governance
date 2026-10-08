# Decision log

Each entry gives the decision, the alternatives considered, and why. Newest entries are last.

### D1. A trained classifier as "the agent"
**Alternatives:**
- An LLM agent.
- A hand-written rule system.

**Decision:** gradient boosting (scikit-learn `HistGradientBoostingClassifier`) per domain, with logistic regression as a second model in E1.

**Why:**
- The governance layer only consumes a (decision, score) pair, so it is agnostic to the agent.
- A classifier gives thousands of decisions per seed with known labels, which makes calibration and regime comparisons measurable.
- No LLM API key was available in the build environment. Nothing in the design depends on one.

### D2. Decisions by the Bayes cost threshold, confidence as P(decision correct)
**Alternatives:**
- A 0.5 threshold with confidence = max(p, 1 − p).

**Decision:** approve when p ≥ C_FA / (C_FA + C_FD). Confidence is p for an approval and 1 − p for a decline.

**Why:**
- The domains have asymmetric costs, and a 0.5 threshold would make the AI-only baseline needlessly bad.
- The consequence, which the console explains, is that confidence can be below 50%. For example, credit declines a likely-good applicant because a bad loan costs 5×.

### D3. Risk = expected cost of executing the AI decision
**Alternatives:**
- Route on confidence only.
- Route on stake only.

**Decision:** expected cost = (1 − confidence) × stake × cost of that error type. Two thresholds give three tiers. YAML rules can only raise a tier.

**Why:**
- It is the quantity a risk owner cares about.
- E3 tests the alternatives as ablations rather than assuming the answer.
- Rules that can only raise a tier keep policies auditable: no rule can silently exempt a case from oversight.

### D4. Policies are versioned YAML with a content hash in every routing record
**Alternatives:**
- Thresholds in code.
- A database-backed rule editor.

**Decision:** `configs/policies/<domain>.yaml`, validated by pydantic. The hash is the SHA-256 of the canonical JSON, truncated to 12 hex characters.

**Why:** any recorded decision can be traced to the exact policy text that routed it, and policies diff cleanly in review.

### D5. Thresholds tuned on separate seeds
**Decision:** thresholds were chosen on tuning seeds 100–104, so that about 20% of cases go to a person and about 5% to approval, then rounded. Reported seeds start at 20261008.

**Why:** tuning on the reported seeds would flatter the risk-adaptive regime.

### D6. A parametric reviewer model instead of claims about people
**Context:** no human participants were available.

**Alternatives:**
- Present simulated reviewers as if measured (rejected, integrity rule).
- Drop human regimes.

**Decision:**
- Reviewers judge the realised outcome with accuracy falling with case difficulty.
- They defer to the AI with a mode-dependent probability (automation bias), take log-normal handling time, fatigue under continuous load and work a staffed priority queue.
- Every parameter is stated, and E4 varies the important ones.

**Why:**
- The governance question is about trade-offs, which a model can expose as long as it is labelled as one.
- The console's live queue records real reviewer decisions, so the same software can run a human study (pending).

### D7. Case difficulty from an independent reference model
**Alternatives:** difficulty from the agent's own confidence.

**Decision:** a logistic regression fitted on the train split (the true probability for payments) defines difficulty d = 1 − |2p − 1|.

**Why:** if difficulty came from the evaluated agent, reviewers would be artificially good exactly where the agent is unsure, which would bias results toward risk-adaptive routing.

### D8. Common random numbers across regimes
**Decision:**
- Each seed draws once per case the reviewer's judgement, deference and time variables, plus arrival times (`CaseDraws`).
- Every regime reuses them.

**Why:** regime differences then reflect routing, not reviewer luck. This is also what justifies paired tests over seeds.

### D9. Seeds as the unit of resampling, paired sign-flip tests, Holm per domain
**Alternatives:** treat cases as independent.

**Decision:** each seed refits the split, model, calibrator and reviewer draws. CIs bootstrap seed means, paired tests flip signs of per-seed differences, and Holm adjusts within each domain and metric (E2) or within each domain (E3 matched comparison).

**Why:** cases within a seed share a fitted model and policy, so treating them as independent would understate uncertainty.

E1's 24 calibration contrasts are reported unadjusted and labelled as such.

### D10. Isotonic as the default calibrator, kept after E1
**Decision:** isotonic regression was fixed as the default before E1. E1 then showed it no better than none or Platt on the large domains, and worse than Platt on credit.

**Why kept:** changing the calibrator after seeing E1 and re-running E2 would be a garden-of-forking-paths choice. The report states the result and its implication instead.

### D11. Fixed routing-score ties in E3 (re-run)
**Context:** the first E3 run (`results/e3_frontier/20261008T013352Z-cc94fe5`, kept for the record) used `score >= quantile` thresholds.
- Constant scores, such as unit stakes in eligibility, sent everyone to review at any target share.
- Plateaus of isotonic scores overshot the target share.

**Decision:** add a 1e-9-scale random jitter to break ties (`ff545cc`) and re-run E3. Only the re-run is reported.

**Why:** the bug made "stake only" routing in eligibility meaningless. With unit stakes it now behaves as random audit, which is the correct reading.

### D12. Loss as the primary outcome, accuracy secondary
**Decision:** loss = summed cost of wrong final decisions per 1,000 cases, in stake units.

**Why:**
- Under asymmetric costs, accuracy rewards the wrong behaviour; credit's cost-optimal agent has 56% accuracy by design.
- Both are reported, together with workload and time, so trade-offs stay visible.

### D13. Reviewer identity comes from the token, not the request
**Alternatives:**
- One shared token with a reviewer name in the body.
- No authentication on localhost.

**Decision:**
- `GOVERNANCE_REVIEWER_TOKENS` holds `name:token` pairs. A decision's actor is the name bound to the presented `X-Reviewer-Token`.
- With no tokens configured, writes are disabled (403).
- The read token (`GOVERNANCE_API_TOKEN`) is separate.

**Why:** an audit log is only as good as its identities, and a client-supplied name would be forgeable.

### D14. Hash-chained audit log in SQLite
**Alternatives:**
- A plain table.
- An external append-only store.

**Decision:** each event stores the hash of the previous event over its canonical fields. `/api/audit/verify` recomputes the chain.

**Why:**
- It gives tamper-evidence without infrastructure. A test edits a stored event and checks that verification fails at that event.
- Limitation: someone with write access to the file could rewrite the whole chain. Anchoring the head hash externally would close that gap and is not implemented.

### D15. Ground truth hidden until a decision exists
**Decision:** the queue and case APIs omit the label for pending cases and reveal it after a decision, as "simulated outcome".

**Why:** showing it earlier would make the review queue meaningless, both as a demo and as a study instrument.

### D16. Mandatory approval needs a written justification; overrides need a reason
**Decision:** at least 10 characters, enforced by the API (pydantic for overrides, the store for approvals) and mirrored in the UI.

**Why:** the spec distinguishes approval from review. A justification requirement is the observable difference, and it makes the audit log useful.

### D17. Results committed to the repository
**Decision:** `results/` (about 3.9 MB) is committed with the run that produced each table.

**Why:** the console and report then work from a fresh clone without a 30-minute re-run, and every number is traceable to a run directory and commit.

### D18. Deviations from the plan
- `docs/PLAN.md` listed a separate `simulator/` package. The stream builder lives in `experiments/stream.py` and the reviewer and queue simulation in `humans/`.
- Error attribution has four causes, not five. "Policy rule forced a path" is not a cause of error. Rules change which path a case takes, which the tier breakdown shows.
- Eligibility uses unit stakes with asymmetric costs. The "vulnerability flag" mentioned in the plan was not implemented.
- E4 varies review time as well as deference, hard-case accuracy and staffing.
