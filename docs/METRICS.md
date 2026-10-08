# Metrics

All metrics are computed in `src/governance/regimes/regimes.py::outcome_metrics` (regimes) and
`src/governance/confidence/calibration.py` (calibration) on the held-out test stream of one seed,
then aggregated over seeds (`src/governance/experiments/stats.py`).

## Outcome

| Metric | Definition |
|---|---|
| Accuracy | Share of final decisions that equal the correct action (dataset label, or simulated payment outcome) |
| Error rate | 1 − accuracy |
| Loss per 1,000 | Σ over wrong final decisions of stake × cost of that error type, divided by cases, × 1,000. Credit: false approval 5, false decline 1, × credit amount (DM). Eligibility: false grant 1, false denial 3, unit stakes. Payments: false approval 1, false rejection 0.25, × amount |
| High-stake errors per 1,000 | Wrong final decisions on cases whose stake is at or above the 90th percentile of training stakes (undefined for unit stakes) |
| Loss avoided per reviewer hour | (AI-only loss − regime loss) / regime reviewer hours, from seed means |

## Workload and time

| Metric | Definition |
|---|---|
| Share to a human | Share of cases a person decides, reviews or approves |
| Reviewer hours per 1,000 | Simulated handling minutes / 60, per 1,000 cases |
| Decision time | Minutes from arrival to final decision through the staffed queue (wait + handling). Autonomous decisions take 0. Reported as median and 95th percentile over all cases |
| Utilisation | Busy reviewer time / (reviewers × elapsed stream time) |

## Oversight behaviour (trust proxies)

These describe **simulated** reviewers on cases where the AI's decision was shown (review or approval). They are proxies for trust, not measurements of it.

| Metric | Definition |
|---|---|
| Override rate | Share of shown cases where the final decision differs from the AI's |
| Override precision | Share of overrides that are correct |
| Automation bias | Among shown cases where the AI was wrong, the share where the reviewer kept the AI decision |
| Appropriate reliance | Share of shown cases where the reviewer kept a correct AI decision or overrode a wrong one |

## Error attribution

Each wrong final decision gets exactly one cause:

- **Autonomous AI error:** executed without a person.
- **Accepted wrong AI:** shown to a person, who kept it.
- **Harmful override:** shown to a person, who overturned a correct AI decision.
- **Unaided human error:** human-only regime.

These are reported per 1,000 cases. They are also broken down by tier, as the final error rate within each tier, and by group (sex and age band for credit, sex and race for eligibility, region for payments). Groups are used only for error analysis, never for routing.

## Calibration

These metrics apply to the *decision confidence*, the estimated probability that the action taken is correct.

| Metric | Definition |
|---|---|
| ECE | Σ_b (n_b / n) · \|accuracy_b − mean confidence_b\| over 15 equal-mass bins |
| MCE | max_b \|accuracy_b − mean confidence_b\| |
| Brier | mean (p − y)², where p = P(positive action correct) |
| NLL | −mean [y log p + (1 − y) log(1 − p)] |
| MAE to true p | Payments only: mean \|p − true probability\| |
| Bayes Brier | Payments only: Brier score of the true probability (the irreducible floor) |

## Statistics

- **Seeds** are independent replications: new split, newly fitted model and calibrator, new reviewer draws.
- **Intervals:** mean and 95% percentile bootstrap CI of the mean over seeds (2,000 resamples).
- **Paired comparisons:** the mean of per-seed differences, its bootstrap CI, and a two-sided sign-flip permutation p-value (10,000 permutations), Holm-adjusted within a family (stated per table).
