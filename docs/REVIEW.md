# Internal Review Board

Seven reviews of release 1.0.0, each from a different perspective. Every finding lists what was checked, what was found and what happened to it: **fixed** (changed before release, with the evidence), **verified** (checked and found to hold, with the test that shows it), **accepted** (a known limitation, documented) or **open** (needs something not available in this environment). The author carried out these reviews against the checks named. They are not independent external reviews.

## Summary

| Reviewer | Verdict | Fixed | Accepted | Open |
|---|---|---|---|---|
| Research | Approve with stated scope | 4 | 4 | 1 |
| Engineering | Approve | 3 | 2 | 0 |
| QA | Approve | 0 | 1 | 0 |
| Security | Approve for local / trusted-network use | 2 | 4 | 0 |
| UX / accessibility | Approve | 5 | 1 | 0 |
| Recruiter | Approve | 0 | 1 | 0 |
| PhD supervisor | Approve as a simulation study; human study required for trust claims | 0 | 2 | 1 |

The open items are the human study (R9 and P3, one study) and nothing else.

## 1. Research reviewer

Checked: every number in `research/REPORT.md` and `README.md` against `research/generated/results.md`; that each claim follows from the analysis cited; that tuning and reporting seeds are disjoint.

| # | Finding | Status |
|---|---|---|
| R1 | The first E3 run used `score >= quantile` thresholds. Constant scores (unit stakes in eligibility) sent every case to review at any target share, so "stake only" routing was meaningless. | **Fixed:** random tie-breaking at 1e-9 scale (`ff545cc`), E3 re-run; the old run is kept for the record (D11). |
| R2 | Several report figures were hand-derived and did not match the generated tables (gap recovery, the E4 range, the interpolated review-only loss). | **Fixed:** corrected to 55%, 39.3k–74.6k and about 206k, each traceable to `results.md`. |
| R3 | "Loss avoided per reviewer hour", the report's efficiency argument, was computed by hand. | **Fixed:** generated table in `results.md` (3,810 risk-adaptive, 831 human only, 679 blanket approval in payments). |
| R4 | `docs/PLAN.md` described a `simulator/` package, a vulnerability flag and five error causes that were never built. | **Fixed:** plan corrected, deviations recorded as D18; the empty `simulator` package was removed. |
| R5 | Isotonic calibration was fixed as the default before E1, and E1 shows it no better than none or Platt. | **Accepted:** kept to avoid choosing after seeing the results (D10); stated in the report. |
| R6 | Simulated reviewers judge against the realised outcome and may know more than the features show, which favours human-only regimes in payments. | **Accepted:** first threat in report §6; the information-limited variant is listed as not run. |
| R7 | Credit has 200 test cases per seed, so no regime difference is significant there. | **Accepted:** reported as noise, not as a null finding. |
| R8 | The E5 concept shift touches about 6% of payments and is a weak test. | **Accepted:** reported as such, not as robustness evidence. |
| R9 | Trust is measured only through simulated proxies. | **Open:** the human study needs participants; the console is ready to serve as the instrument. |

## 2. Engineering reviewer

Checked: module boundaries, typing (`mypy` strict on `src` and `tests`), determinism, provenance of results, the CLI.

| # | Finding | Status |
|---|---|---|
| E1 | The store shared one SQLite connection across threads. A read could run inside another thread's open write transaction. | **Fixed:** every statement takes the store's lock (`9fdc7f5`); `test_concurrent_decisions_keep_one_winner_and_a_valid_chain` races 5 deciders per case over 20 cases on 16 threads, with concurrent reads, and checks one winner per case and an intact chain. |
| E2 | Five experiments in parallel oversubscribed the CPU (load 17) through BLAS and OpenMP threads. | **Fixed:** `scripts/reproduce.sh` exports `OMP_NUM_THREADS=1`. |
| E3 | Report regeneration must be deterministic for results to be checkable. | **Fixed:** verified byte-identical output from the committed runs; CI now fails if `governance report` changes `research/`. |
| E4 | The regime simulator replays one queue per regime in Python; E4 takes about 16 minutes. | **Accepted:** fast enough for the study; vectorising the queue is not needed for any claim. |
| E5 | `results/` (about 3.9 MB) is committed. | **Accepted:** the console and report work from a fresh clone, and every number keeps its run directory and commit (D17). |

## 3. QA reviewer

Checked: the unit, API and browser suites; error paths; that tests cover the behaviour the README claims.

| # | Finding | Status |
|---|---|---|
| Q1 | Does the API enforce the approval tier's justification, or only the UI? | **Verified:** the store rejects an approval without a 10-character reason (`test_approval_needs_justification_and_override_flips`). |
| Q2 | Does ground truth stay hidden until a decision? | **Verified:** `test_queue_is_ordered_and_hides_labels`, and the browser flow shows the outcome only after `a`. |
| Q3 | Is tamper evidence demonstrated, not just claimed? | **Verified:** `test_stats_and_audit_chain` edits a stored event and checks that verification fails at it; the browser flow verifies "Intact" after real decisions. |
| Q4 | Browser tests need Chromium and a built frontend, so they are opt-in (`-m ui`). | **Accepted:** CI runs them in a separate job after the build. |

Final counts: 29 unit and API tests, 25 browser tests (9 views × 2 viewports, the case inspector, the reviewer flow, error states and axe in 2 themes × 2 viewports), all passing.

## 4. Security reviewer

Checked: authentication and identity, rate limiting, input validation, headers, secrets in the working tree and in git history, dependency advisories.

| # | Finding | Status |
|---|---|---|
| S1 | `react-router-dom` 6.30 carried an open-redirect advisory (GHSA-wrjc-x8rr-h8h6). | **Fixed:** upgraded to 7.18.4 (`3362fbf`); `npm audit --omit=dev` reports 0. |
| S2 | A test fixture used a token that looked like a real secret. | **Fixed:** renamed to an obvious test value. A scan of the full git history for keys, tokens and private-key headers found nothing. |
| S3 | `GOVERNANCE_API_TOKEN` protects reads for headless use, but the console does not send it, so setting it makes the console unusable. | **Accepted:** documented in `.env.example`. A deployment beyond a trusted network should sit behind an authenticating proxy. |
| S4 | The reviewer token is kept in `sessionStorage`, readable by any script on the origin. | **Accepted:** the CSP allows scripts from `'self'` only, the page renders no HTML from data, and the token is cleared when the tab closes. |
| S5 | The hash chain is tamper-evident, not tamper-proof: someone with write access to the file can rewrite the whole chain. | **Accepted:** stated in D14; anchoring the head hash externally would close it. |
| S6 | Vite and esbuild have advisories that affect the development server only. | **Accepted:** the production build is static files served by FastAPI; the dev server is never exposed. |

Also checked and fine: `pip-audit` finds no known vulnerabilities; reviewer identity comes from the token, never the request body (D13); tokens are compared in constant time and must be at least 16 characters; writes are disabled when no reviewers are configured; reads and writes are rate limited per client (writes 1/s, burst 20); path segments are validated before touching the file system; responses carry CSP, `X-Frame-Options: DENY`, `nosniff` and `no-referrer`; nothing logs tokens.

## 5. UX / accessibility reviewer

Checked: every view at 1440 px and 390 px in both themes with axe-core (WCAG 2.1 A/AA plus best practice), keyboard-only operation, loading, empty and error states.

| # | Finding | Status |
|---|---|---|
| U1 | Credit confidence below 50% read as a bug. | **Fixed:** the inspector explains the cost threshold and shows P(positive correct), the threshold and both error costs. |
| U2 | Interval plots were squashed at narrow widths. | **Fixed:** rebuilt as HTML rows with percentage positioning. |
| U3 | E4 small multiples had unreadable text. | **Fixed:** two columns, a shared legend and a shared y-axis. |
| U4 | On mobile the case view lost the page heading (axe `page-has-heading-one`). | **Fixed:** the queue heading stays when a case is open. |
| U5 | Inlined fonts were blocked by the CSP. | **Fixed:** fonts are emitted as files (`assetsInlineLimit: 0`). |
| U6 | Risk tiers use color; colorblind readers need more. | **Accepted as designed:** every tier badge pairs color with a shape (● ▲ ■) and a word. |

axe reports no violations on any view in either theme or viewport.

## 6. Recruiter

Checked: whether someone outside the field understands what the project shows within a minute of opening the README.

| # | Finding | Status |
|---|---|---|
| C1 | The work is a simulation study; a skim could mistake it for evidence about real reviewers. | **Accepted and signposted:** the README states it in its first paragraph, next to the headline table and a screenshot of the console. |

## 7. PhD supervisor

Checked: whether the contribution is stated at the strength the evidence supports.

| # | Finding | Status |
|---|---|---|
| P1 | The headline result depends on reviewers deferring less in mandatory approval (0.2) than in review (0.5). | **Accepted:** stated in the report (RQ3) and varied in E4. |
| P2 | Costs in eligibility and payments are assumptions that set the decision threshold. | **Accepted:** listed as a threat to validity. |
| P3 | Trust, the spec's last metric, cannot be measured in simulation. | **Open:** the same human study as R9. |
