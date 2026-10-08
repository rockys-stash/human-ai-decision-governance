# Generated results

Produced by `governance report` from the latest completed run of each experiment. Do not edit by hand; every table names the run and commit it came from.

## E1: Calibration of decision confidence

_Source: `results/e1_calibration/20261008T013352Z-cc94fe5` · commit `cc94fe5550b1` · 20 seeds from base 20261008 · runtime 503.7 s._

Confidence is the estimated probability that the decision taken is correct. Values are means over seeds with 95% bootstrap CIs; ECE uses 15 equal-mass bins on the test stream.

| Domain | Model | Calibrator | Accuracy (%) | Mean confidence (%) | ECE (pp) | MCE (pp) | Brier | NLL |
|---|---|---|---|---|---|---|---|---|
| credit | gbm | none | 66.7 [65.3, 68.1] | 73.2 [72.0, 74.5] | 10.8 [10.0, 11.6] | 29.1 [26.8, 31.8] | 0.1788 [0.1727, 0.1856] | 0.559 [0.539, 0.582] |
| credit | gbm | Platt | 56.5 [54.6, 58.2] | 57.9 [56.0, 59.9] | 8.7 [8.1, 9.2] | 25.0 [22.4, 27.8] | 0.1716 [0.1670, 0.1770] | 0.517 [0.505, 0.531] |
| credit | gbm | isotonic | 56.3 [53.1, 59.4] | 59.9 [56.7, 63.1] | 9.7 [8.8, 10.7] | 25.6 [23.1, 28.1] | 0.1760 [0.1701, 0.1829] | 0.598 [0.548, 0.657] |
| credit | logreg | none | 61.3 [59.8, 62.7] | 64.6 [63.7, 65.5] | 8.2 [7.4, 9.0] | 24.1 [20.8, 27.4] | 0.1715 [0.1665, 0.1765] | 0.517 [0.503, 0.531] |
| credit | logreg | Platt | 57.5 [55.2, 59.9] | 59.2 [56.7, 61.6] | 8.7 [8.1, 9.3] | 23.4 [21.0, 25.8] | 0.1712 [0.1670, 0.1753] | 0.516 [0.504, 0.527] |
| credit | logreg | isotonic | 60.3 [57.7, 62.7] | 63.7 [60.8, 66.4] | 10.5 [9.4, 11.5] | 29.1 [25.5, 32.8] | 0.1774 [0.1726, 0.1819] | 0.626 [0.580, 0.684] |
| eligibility | gbm | none | 84.6 [84.5, 84.7] | 84.1 [84.0, 84.2] | 0.9 [0.8, 1.0] | 3.1 [2.7, 3.5] | 0.0886 [0.0881, 0.0890] | 0.279 [0.278, 0.281] |
| eligibility | gbm | Platt | 85.2 [85.0, 85.3] | 84.7 [84.5, 84.9] | 1.0 [0.9, 1.1] | 3.8 [3.3, 4.3] | 0.0886 [0.0881, 0.0890] | 0.279 [0.278, 0.281] |
| eligibility | gbm | isotonic | 84.9 [84.7, 85.1] | 84.8 [84.5, 85.1] | 0.9 [0.8, 1.0] | 3.1 [2.7, 3.6] | 0.0887 [0.0883, 0.0891] | 0.281 [0.279, 0.283] |
| eligibility | logreg | none | 82.1 [82.0, 82.2] | 82.3 [82.2, 82.4] | 1.0 [0.9, 1.1] | 3.4 [3.1, 3.7] | 0.1059 [0.1054, 0.1064] | 0.330 [0.328, 0.331] |
| eligibility | logreg | Platt | 82.0 [81.9, 82.1] | 82.0 [81.9, 82.2] | 1.0 [0.9, 1.1] | 3.3 [3.0, 3.5] | 0.1059 [0.1054, 0.1063] | 0.330 [0.329, 0.331] |
| eligibility | logreg | isotonic | 81.8 [81.5, 82.1] | 81.8 [81.5, 82.1] | 1.1 [1.1, 1.2] | 3.5 [3.2, 3.9] | 0.1062 [0.1058, 0.1067] | 0.332 [0.331, 0.334] |
| payments | gbm | none | 83.5 [83.2, 83.8] | 83.2 [83.0, 83.4] | 1.6 [1.5, 1.8] | 4.8 [4.3, 5.5] | 0.0970 [0.0966, 0.0975] | 0.334 [0.333, 0.335] |
| payments | gbm | Platt | 83.3 [83.1, 83.6] | 83.4 [83.1, 83.6] | 1.6 [1.4, 1.7] | 4.4 [3.8, 5.0] | 0.0970 [0.0965, 0.0975] | 0.334 [0.332, 0.335] |
| payments | gbm | isotonic | 83.6 [83.0, 84.1] | 83.8 [83.2, 84.3] | 1.8 [1.6, 2.0] | 5.1 [4.1, 6.2] | 0.0973 [0.0969, 0.0978] | 0.338 [0.336, 0.340] |
| payments | logreg | none | 83.8 [83.6, 84.0] | 83.9 [83.8, 84.0] | 1.5 [1.4, 1.7] | 4.2 [3.7, 4.7] | 0.0962 [0.0959, 0.0967] | 0.332 [0.331, 0.334] |
| payments | logreg | Platt | 83.9 [83.7, 84.1] | 83.9 [83.8, 84.0] | 1.6 [1.4, 1.7] | 4.2 [3.6, 4.8] | 0.0963 [0.0959, 0.0967] | 0.332 [0.331, 0.333] |
| payments | logreg | isotonic | 83.9 [83.5, 84.4] | 84.1 [83.7, 84.5] | 1.7 [1.5, 1.9] | 4.8 [4.0, 5.5] | 0.0967 [0.0963, 0.0971] | 0.337 [0.335, 0.339] |

### Synthetic payments: distance to the known true probability

| Model | Calibrator | Mean abs. error to true p | Brier | Bayes Brier (irreducible) |
|---|---|---|---|---|
| gbm | none | 0.0214 [0.0209, 0.0219] | 0.0970 [0.0966, 0.0975] | 0.0960 [0.0956, 0.0965] |
| gbm | Platt | 0.0209 [0.0204, 0.0214] | 0.0970 [0.0965, 0.0975] | 0.0960 [0.0956, 0.0965] |
| gbm | isotonic | 0.0248 [0.0242, 0.0254] | 0.0973 [0.0969, 0.0978] | 0.0960 [0.0956, 0.0965] |
| logreg | none | 0.0086 [0.0080, 0.0091] | 0.0962 [0.0959, 0.0967] | 0.0960 [0.0956, 0.0965] |
| logreg | Platt | 0.0091 [0.0086, 0.0096] | 0.0963 [0.0959, 0.0967] | 0.0960 [0.0956, 0.0965] |
| logreg | isotonic | 0.0164 [0.0157, 0.0170] | 0.0967 [0.0963, 0.0971] | 0.0960 [0.0956, 0.0965] |

### Does post-hoc calibration help? (paired over seeds, calibrated minus uncalibrated; sign-flip test)

| Domain | Model | Metric | Calibrator | Difference | 95% CI | p |
|---|---|---|---|---|---|---|
| credit | gbm | ECE | Platt | -2.09 pp | [-2.98, -1.22] | <0.001 |
| credit | gbm | Brier | Platt | -0.0072 | [-0.0092, -0.0053] | <0.001 |
| credit | gbm | ECE | isotonic | -1.08 pp | [-2.14, +0.10] | 0.088 |
| credit | gbm | Brier | isotonic | -0.0028 | [-0.0053, -0.0002] | 0.053 |
| credit | logreg | ECE | Platt | +0.51 pp | [-0.26, +1.20] | 0.200 |
| credit | logreg | Brier | Platt | -0.0004 | [-0.0018, +0.0012] | 0.648 |
| credit | logreg | ECE | isotonic | +2.24 pp | [+1.42, +3.08] | <0.001 |
| credit | logreg | Brier | isotonic | +0.0059 | [+0.0039, +0.0077] | <0.001 |
| eligibility | gbm | ECE | Platt | +0.09 pp | [+0.02, +0.16] | 0.028 |
| eligibility | gbm | Brier | Platt | +0.0000 | [-0.0000, +0.0001] | 0.205 |
| eligibility | gbm | ECE | isotonic | -0.04 pp | [-0.15, +0.08] | 0.531 |
| eligibility | gbm | Brier | isotonic | +0.0001 | [+0.0001, +0.0002] | 0.001 |
| eligibility | logreg | ECE | Platt | +0.00 pp | [-0.04, +0.05] | 0.911 |
| eligibility | logreg | Brier | Platt | -0.0000 | [-0.0000, +0.0000] | 0.079 |
| eligibility | logreg | ECE | isotonic | +0.11 pp | [-0.00, +0.23] | 0.068 |
| eligibility | logreg | Brier | isotonic | +0.0003 | [+0.0003, +0.0004] | <0.001 |
| payments | gbm | ECE | Platt | -0.05 pp | [-0.12, +0.01] | 0.161 |
| payments | gbm | Brier | Platt | -0.0000 | [-0.0001, +0.0000] | 0.121 |
| payments | gbm | ECE | isotonic | +0.15 pp | [-0.08, +0.37] | 0.193 |
| payments | gbm | Brier | isotonic | +0.0003 | [+0.0002, +0.0005] | <0.001 |
| payments | logreg | ECE | Platt | +0.00 pp | [-0.04, +0.04] | 0.949 |
| payments | logreg | Brier | Platt | +0.0000 | [-0.0000, +0.0000] | 0.415 |
| payments | logreg | ECE | isotonic | +0.16 pp | [-0.10, +0.41] | 0.249 |
| payments | logreg | Brier | isotonic | +0.0004 | [+0.0003, +0.0006] | <0.001 |

## E2: Four oversight regimes

_Source: `results/e2_regimes/20261008T013352Z-cc94fe5` · commit `cc94fe5550b1` · 20 seeds from base 20261008 · runtime 125.7 s._

Means over seeds with 95% bootstrap CIs. Loss is the cost of wrong final decisions per 1,000 cases in the domain's stake units. Decision time is from arrival to final decision (0 for autonomous decisions).

### Credit (German Credit)

Policy `credit-default` v1.0 (hash `fbf386ab6a15`).

| Regime | Accuracy (%) | Loss / 1,000 | Share to a human (%) | Reviewer hours / 1,000 | Decision min, median | Decision min, p95 | High-stake errors / 1,000 |
|---|---|---|---|---|---|---|---|
| Human only | 78.6 [77.6, 79.6] | 1945159 [1750416, 2143650] | 100.0 [100.0, 100.0] | 121.4 [119.1, 123.9] | 12.6 [11.2, 14.2] | 26.9 [24.1, 30.0] | 20.75 [17.00, 24.50] |
| AI only | 56.3 [53.1, 59.4] | 1920738 [1784649, 2062631] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 42.50 [34.75, 50.50] |
| AI + blanket approval | 74.0 [72.5, 75.4] | 1947690 [1763846, 2129185] | 100.0 [100.0, 100.0] | 121.4 [119.1, 123.9] | 12.6 [11.2, 14.2] | 26.9 [24.1, 30.0] | 25.25 [21.00, 29.25] |
| Risk-adaptive oversight | 59.9 [57.1, 62.7] | 1930192 [1785191, 2081290] | 23.1 [21.3, 25.1] | 15.0 [13.6, 16.5] | 0.0 [0.0, 0.0] | 5.1 [4.7, 5.6] | 26.50 [22.00, 30.75] |

Loss avoided per reviewer hour relative to AI only (ratio of seed means; negative = oversight added loss): Human only -201.1; AI + blanket approval -221.9; Risk-adaptive oversight -628.6.

Oversight behaviour on cases where a reviewer saw the AI's decision:

| Regime | Override rate (%) | Override precision (%) | Automation bias (%) | Appropriate reliance (%) | Reviewer utilisation (%) |
|---|---|---|---|---|---|
| AI + blanket approval | 35.7 [33.5, 37.9] | 74.2 [71.4, 76.8] | 39.2 [37.1, 41.2] | 74.0 [72.5, 75.4] | 85.6 [83.4, 88.2] |
| Risk-adaptive oversight | 28.3 [25.7, 30.7] | 78.2 [73.1, 83.3] | 56.9 [53.7, 60.4] | 64.3 [60.8, 67.5] | 10.9 [10.0, 12.0] |

Error attribution (wrong final decisions per 1,000 cases, by cause):

| Regime | Autonomous AI error | Reviewer accepted a wrong AI decision | Harmful override | Unaided human error |
|---|---|---|---|---|
| Human only | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 213.8 [203.7, 224.2] |
| AI only | 437.0 [405.7, 468.5] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| AI + blanket approval | 0.0 [0.0, 0.0] | 170.0 [157.2, 184.8] | 90.2 [83.0, 98.2] | 0.0 [0.0, 0.0] |
| Risk-adaptive oversight | 318.2 [294.7, 342.8] | 68.0 [58.5, 78.0] | 14.2 [10.8, 18.0] | 0.0 [0.0, 0.0] |

Risk-adaptive routing by tier:

| Tier | Share of cases (%) | Final error rate in tier (%) |
|---|---|---|
| autonomous | 76.9 [74.9, 78.7] | 41.5 [38.2, 44.9] |
| review | 16.6 [15.1, 18.1] | 39.8 [35.6, 43.9] |
| approval | 6.6 [5.8, 7.3] | 25.2 [19.3, 32.2] |

Policy rules fired (share of cases): `large-exposure` 3.8%, `long-term` 6.5%.

Group breakdown, risk-adaptive regime (error-analysis only; groups are not used for routing):

| Group | Level | Final error rate (%) | Share to a human (%) |
|---|---|---|---|
| sex | female | 43.2 [39.6, 46.8] | 20.1 [17.5, 22.9] |
| sex | male | 38.5 [35.7, 41.4] | 24.6 [22.6, 26.4] |
| age_band | 25 and over | 39.1 [36.1, 42.3] | 24.1 [22.0, 26.2] |
| age_band | under 25 | 45.3 [41.9, 48.6] | 17.5 [14.4, 20.4] |

Paired comparisons (A minus B over seeds; sign-flip test, Holm-adjusted within each metric and domain):

| Metric | A | B | A - B | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| loss_per_1000 | Human only | AI only | +24421.5 | [-236063.8, +304923.2] | 1.000 |
| accuracy | Human only | AI only | +22.33 pp | [+18.95, +25.63] | <0.001 |
| reviewer_hours_per_1000 | Human only | AI only | +121.4 | [+119.1, +123.9] | <0.001 |
| loss_per_1000 | Human only | AI + blanket approval | -2531.0 | [-91049.0, +85744.6] | 1.000 |
| accuracy | Human only | AI + blanket approval | +4.65 pp | [+3.57, +5.88] | <0.001 |
| reviewer_hours_per_1000 | Human only | AI + blanket approval | +0.0 | [+0.0, +0.0] | 1.000 |
| loss_per_1000 | Human only | Risk-adaptive oversight | +14967.8 | [-117071.6, +124715.2] | 1.000 |
| accuracy | Human only | Risk-adaptive oversight | +18.68 pp | [+15.80, +21.53] | <0.001 |
| reviewer_hours_per_1000 | Human only | Risk-adaptive oversight | +106.4 | [+104.2, +108.9] | <0.001 |
| loss_per_1000 | AI only | AI + blanket approval | -26952.5 | [-293833.7, +231484.9] | 1.000 |
| accuracy | AI only | AI + blanket approval | -17.68 pp | [-20.20, -14.95] | <0.001 |
| reviewer_hours_per_1000 | AI only | AI + blanket approval | -121.4 | [-123.9, -119.1] | <0.001 |
| loss_per_1000 | AI only | Risk-adaptive oversight | -9453.7 | [-204839.0, +180580.4] | 1.000 |
| accuracy | AI only | Risk-adaptive oversight | -3.65 pp | [-4.55, -2.85] | <0.001 |
| reviewer_hours_per_1000 | AI only | Risk-adaptive oversight | -15.0 | [-16.5, -13.6] | <0.001 |
| loss_per_1000 | AI + blanket approval | Risk-adaptive oversight | +17498.8 | [-107211.2, +138575.3] | 1.000 |
| accuracy | AI + blanket approval | Risk-adaptive oversight | +14.02 pp | [+11.75, +16.25] | <0.001 |
| reviewer_hours_per_1000 | AI + blanket approval | Risk-adaptive oversight | +106.4 | [+104.2, +108.9] | <0.001 |

### Eligibility (Adult)

Policy `eligibility-default` v1.0 (hash `477f51ef511d`).

| Regime | Accuracy (%) | Loss / 1,000 | Share to a human (%) | Reviewer hours / 1,000 | Decision min, median | Decision min, p95 | High-stake errors / 1,000 |
|---|---|---|---|---|---|---|---|
| Human only | 81.3 [81.2, 81.5] | 439 [434, 443] | 100.0 [100.0, 100.0] | 114.9 [114.7, 115.2] | 10.7 [10.4, 11.0] | 30.5 [28.9, 32.3] | n/a |
| AI only | 84.9 [84.7, 85.1] | 165 [164, 166] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | n/a |
| AI + blanket approval | 82.1 [81.9, 82.2] | 383 [379, 388] | 100.0 [100.0, 100.0] | 114.9 [114.7, 115.2] | 10.7 [10.4, 11.0] | 30.5 [28.9, 32.3] | n/a |
| Risk-adaptive oversight | 87.3 [87.2, 87.4] | 166 [164, 167] | 21.9 [21.1, 22.6] | 14.0 [13.2, 14.7] | 0.0 [0.0, 0.0] | 4.9 [4.6, 5.1] | n/a |

Loss avoided per reviewer hour relative to AI only (ratio of seed means; negative = oversight added loss): Human only -2.4; AI + blanket approval -1.9; Risk-adaptive oversight -0.0.

Oversight behaviour on cases where a reviewer saw the AI's decision:

| Regime | Override rate (%) | Override precision (%) | Automation bias (%) | Appropriate reliance (%) | Reviewer utilisation (%) |
|---|---|---|---|---|---|
| AI + blanket approval | 20.2 [20.0, 20.4] | 42.9 [42.2, 43.5] | 42.7 [42.2, 43.3] | 82.1 [81.9, 82.2] | 86.3 [85.8, 86.7] |
| Risk-adaptive oversight | 27.6 [27.0, 28.1] | 69.7 [68.6, 70.6] | 58.6 [57.6, 59.6] | 64.5 [63.7, 65.2] | 10.5 [9.9, 11.0] |

Error attribution (wrong final decisions per 1,000 cases, by cause):

| Regime | Autonomous AI error | Reviewer accepted a wrong AI decision | Harmful override | Unaided human error |
|---|---|---|---|---|
| Human only | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 186.9 [185.3, 188.5] |
| AI only | 150.8 [148.6, 153.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| AI + blanket approval | 0.0 [0.0, 0.0] | 64.4 [63.1, 65.6] | 115.1 [113.5, 116.9] | 0.0 [0.0, 0.0] |
| Risk-adaptive oversight | 49.3 [47.0, 51.9] | 59.3 [57.6, 61.2] | 18.2 [17.5, 18.9] | 0.0 [0.0, 0.0] |

Risk-adaptive routing by tier:

| Tier | Share of cases (%) | Final error rate in tier (%) |
|---|---|---|
| autonomous | 78.1 [77.4, 78.9] | 6.3 [6.1, 6.6] |
| review | 17.1 [16.3, 17.8] | 36.8 [35.9, 37.7] |
| approval | 4.8 [4.2, 5.3] | 31.1 [29.6, 32.4] |

Policy rules fired (share of cases): `uncertain-denial` 3.2%.

Group breakdown, risk-adaptive regime (error-analysis only; groups are not used for routing):

| Group | Level | Final error rate (%) | Share to a human (%) |
|---|---|---|---|
| sex | Female | 6.4 [6.2, 6.5] | 8.2 [7.9, 8.6] |
| sex | Male | 15.8 [15.7, 16.0] | 28.7 [27.6, 29.6] |
| race | Amer-Indian-Eskimo | 7.9 [6.9, 8.9] | 11.0 [9.4, 12.7] |
| race | Asian-Pac-Islander | 14.4 [13.7, 15.0] | 24.9 [23.7, 26.1] |
| race | Black | 6.8 [6.5, 7.1] | 9.9 [9.1, 10.6] |
| race | Other | 7.6 [6.4, 9.0] | 8.2 [6.6, 9.7] |
| race | White | 13.4 [13.2, 13.5] | 23.4 [22.6, 24.1] |

Paired comparisons (A minus B over seeds; sign-flip test, Holm-adjusted within each metric and domain):

| Metric | A | B | A - B | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| loss_per_1000 | Human only | AI only | +273.5 | [+269.1, +278.1] | <0.001 |
| accuracy | Human only | AI only | -3.61 pp | [-3.91, -3.31] | <0.001 |
| reviewer_hours_per_1000 | Human only | AI only | +114.9 | [+114.7, +115.2] | <0.001 |
| loss_per_1000 | Human only | AI + blanket approval | +55.4 | [+53.5, +57.3] | <0.001 |
| accuracy | Human only | AI + blanket approval | -0.74 pp | [-0.84, -0.64] | <0.001 |
| reviewer_hours_per_1000 | Human only | AI + blanket approval | +0.0 | [+0.0, +0.0] | 1.000 |
| loss_per_1000 | Human only | Risk-adaptive oversight | +273.1 | [+268.3, +278.3] | <0.001 |
| accuracy | Human only | Risk-adaptive oversight | -6.00 pp | [-6.20, -5.80] | <0.001 |
| reviewer_hours_per_1000 | Human only | Risk-adaptive oversight | +100.9 | [+100.2, +101.6] | <0.001 |
| loss_per_1000 | AI only | AI + blanket approval | -218.2 | [-222.8, -213.5] | <0.001 |
| accuracy | AI only | AI + blanket approval | +2.87 pp | [+2.61, +3.13] | <0.001 |
| reviewer_hours_per_1000 | AI only | AI + blanket approval | -114.9 | [-115.2, -114.7] | <0.001 |
| loss_per_1000 | AI only | Risk-adaptive oversight | -0.4 | [-2.2, +1.2] | 0.655 |
| accuracy | AI only | Risk-adaptive oversight | -2.39 pp | [-2.58, -2.20] | <0.001 |
| reviewer_hours_per_1000 | AI only | Risk-adaptive oversight | -14.0 | [-14.7, -13.2] | <0.001 |
| loss_per_1000 | AI + blanket approval | Risk-adaptive oversight | +217.8 | [+213.1, +222.8] | <0.001 |
| accuracy | AI + blanket approval | Risk-adaptive oversight | -5.25 pp | [-5.41, -5.12] | <0.001 |
| reviewer_hours_per_1000 | AI + blanket approval | Risk-adaptive oversight | +100.9 | [+100.2, +101.6] | <0.001 |

### Payments (synthetic)

Policy `payments-default` v1.0 (hash `0bc9757cbf19`).

| Regime | Accuracy (%) | Loss / 1,000 | Share to a human (%) | Reviewer hours / 1,000 | Decision min, median | Decision min, p95 | High-stake errors / 1,000 |
|---|---|---|---|---|---|---|---|
| Human only | 83.3 [83.0, 83.6] | 147119 [141328, 153691] | 100.0 [100.0, 100.0] | 111.8 [111.3, 112.3] | 9.5 [9.3, 9.8] | 26.2 [24.2, 28.5] | 20.14 [18.91, 21.43] |
| AI only | 83.6 [83.0, 84.1] | 239973 [233631, 245927] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 24.15 [23.05, 25.32] |
| AI + blanket approval | 83.4 [83.0, 83.8] | 164100 [159002, 169781] | 100.0 [100.0, 100.0] | 111.8 [111.3, 112.3] | 9.5 [9.3, 9.8] | 26.2 [24.2, 28.5] | 20.48 [19.35, 21.70] |
| Risk-adaptive oversight | 85.2 [84.7, 85.6] | 188883 [183726, 193965] | 23.5 [23.1, 23.9] | 13.4 [13.1, 13.7] | 0.0 [0.0, 0.0] | 4.5 [4.4, 4.6] | 18.34 [17.41, 19.38] |

Loss avoided per reviewer hour relative to AI only (ratio of seed means; negative = oversight added loss): Human only 830.6; AI + blanket approval 678.7; Risk-adaptive oversight 3,810.4.

Oversight behaviour on cases where a reviewer saw the AI's decision:

| Regime | Override rate (%) | Override precision (%) | Automation bias (%) | Appropriate reliance (%) | Reviewer utilisation (%) |
|---|---|---|---|---|---|
| AI + blanket approval | 21.0 [20.6, 21.4] | 49.7 [48.6, 50.6] | 36.6 [35.9, 37.3] | 83.4 [83.0, 83.8] | 83.8 [83.1, 84.5] |
| Risk-adaptive oversight | 21.2 [20.4, 22.0] | 66.0 [63.7, 68.1] | 55.3 [54.1, 56.5] | 75.5 [74.3, 76.6] | 10.1 [9.8, 10.3] |

Error attribution (wrong final decisions per 1,000 cases, by cause):

| Regime | Autonomous AI error | Reviewer accepted a wrong AI decision | Harmful override | Unaided human error |
|---|---|---|---|---|
| Human only | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 167.0 [163.9, 170.3] |
| AI only | 164.4 [159.0, 170.2] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| AI + blanket approval | 0.0 [0.0, 0.0] | 60.3 [57.6, 63.2] | 105.4 [103.0, 107.9] | 0.0 [0.0, 0.0] |
| Risk-adaptive oversight | 90.9 [88.5, 93.1] | 40.7 [38.3, 43.2] | 16.9 [15.8, 18.0] | 0.0 [0.0, 0.0] |

Risk-adaptive routing by tier:

| Tier | Share of cases (%) | Final error rate in tier (%) |
|---|---|---|
| autonomous | 76.5 [76.1, 76.9] | 11.9 [11.6, 12.1] |
| review | 18.3 [18.0, 18.6] | 25.7 [24.4, 27.0] |
| approval | 5.2 [5.0, 5.4] | 20.2 [18.9, 21.4] |

Policy rules fired (share of cases): `changed-bank-details` 5.9%, `large-payment` 0.4%.

Group breakdown, risk-adaptive regime (error-analysis only; groups are not used for routing):

| Group | Level | Final error rate (%) | Share to a human (%) |
|---|---|---|---|
| region | east | 14.2 [13.7, 14.7] | 22.5 [21.8, 23.2] |
| region | north | 14.9 [14.4, 15.4] | 23.1 [22.4, 23.7] |
| region | south | 15.4 [15.0, 15.9] | 23.9 [23.4, 24.4] |
| region | west | 14.8 [14.1, 15.6] | 24.5 [24.0, 25.0] |

Paired comparisons (A minus B over seeds; sign-flip test, Holm-adjusted within each metric and domain):

| Metric | A | B | A - B | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| loss_per_1000 | Human only | AI only | -92854.0 | [-101830.4, -82125.9] | <0.001 |
| accuracy | Human only | AI only | -0.25 pp | [-0.82, +0.28] | 0.804 |
| reviewer_hours_per_1000 | Human only | AI only | +111.8 | [+111.3, +112.3] | <0.001 |
| loss_per_1000 | Human only | AI + blanket approval | -16981.2 | [-20558.7, -13027.9] | <0.001 |
| accuracy | Human only | AI + blanket approval | -0.12 pp | [-0.34, +0.08] | 0.804 |
| reviewer_hours_per_1000 | Human only | AI + blanket approval | +0.0 | [+0.0, +0.0] | 1.000 |
| loss_per_1000 | Human only | Risk-adaptive oversight | -41763.4 | [-47907.4, -35385.2] | <0.001 |
| accuracy | Human only | Risk-adaptive oversight | -1.85 pp | [-2.27, -1.42] | <0.001 |
| reviewer_hours_per_1000 | Human only | Risk-adaptive oversight | +98.4 | [+98.0, +98.8] | <0.001 |
| loss_per_1000 | AI only | AI + blanket approval | +75872.8 | [+66697.3, +84018.8] | <0.001 |
| accuracy | AI only | AI + blanket approval | +0.13 pp | [-0.28, +0.57] | 0.804 |
| reviewer_hours_per_1000 | AI only | AI + blanket approval | -111.8 | [-112.3, -111.3] | <0.001 |
| loss_per_1000 | AI only | Risk-adaptive oversight | +51090.6 | [+44067.5, +57529.8] | <0.001 |
| accuracy | AI only | Risk-adaptive oversight | -1.60 pp | [-1.84, -1.35] | <0.001 |
| reviewer_hours_per_1000 | AI only | Risk-adaptive oversight | -13.4 | [-13.7, -13.1] | <0.001 |
| loss_per_1000 | AI + blanket approval | Risk-adaptive oversight | -24782.2 | [-28912.2, -20527.3] | <0.001 |
| accuracy | AI + blanket approval | Risk-adaptive oversight | -1.73 pp | [-2.07, -1.39] | <0.001 |
| reviewer_hours_per_1000 | AI + blanket approval | Risk-adaptive oversight | +98.4 | [+98.0, +98.8] | <0.001 |

## E3: Loss-workload frontier and routing ablations

_Source: `results/e3_frontier/20261008T014004Z-ff545cc` · commit `ff545cc86790` · 20 seeds from base 20261008 · runtime 161.1 s._

Each router sends its top share of cases (by its score, threshold set on the calibration split) to `review`; the rest run autonomously. Loss per 1,000 cases, mean [95% CI].

### Credit (German Credit)

| Router | 0% | 5% | 10% | 15% | 20% | 30% | 40% | 50% | 75% | 100% |
|---|---|---|---|---|---|---|---|---|---|---|
| Expected cost (calibrated) | 1920738 | 2001502 | 2004320 | 1971700 | 1999034 | 1957540 | 1958862 | 1964666 | 1952094 | 2017054 |
| Expected cost (uncalibrated) | 1920738 | 1974697 | 2030850 | 2047980 | 2033383 | 2059071 | 2064340 | 2038016 | 1998057 | 2017054 |
| Confidence only | 1920738 | 1924008 | 1899161 | 1899137 | 1908130 | 1919101 | 1887310 | 1915392 | 1984150 | 2017054 |
| Stake only | 1920738 | 2051779 | 2051806 | 2006090 | 2051240 | 2033677 | 2048929 | 2022455 | 1992384 | 2017054 |
| Random audit | 1920738 | 1931568 | 1922600 | 1901859 | 1927686 | 1945036 | 1983585 | 1972797 | 2006240 | 2017054 |

Configured policy: loss 1930192 [1785191, 2081290] per 1,000 with 23.1 [21.3, 25.1]% of cases to a human and 15.0 [13.6, 16.5] reviewer hours per 1,000.

At a matched 20% review share (expected cost, calibrated, minus each alternative; Holm-adjusted):

| Alternative router | Loss difference / 1,000 | 95% CI | p (Holm) |
|---|---|---|---|
| Expected cost (uncalibrated) | -34348.5 | [-93106.6, +10594.1] | 0.713 |
| Confidence only | +90904.0 | [-82138.8, +273831.3] | 0.713 |
| Stake only | -52205.2 | [-125541.6, +9908.3] | 0.666 |
| Random audit | +71348.8 | [-83603.1, +239594.0] | 0.713 |

### Eligibility (Adult)

| Router | 0% | 5% | 10% | 15% | 20% | 30% | 40% | 50% | 75% | 100% |
|---|---|---|---|---|---|---|---|---|---|---|
| Expected cost (calibrated) | 165 | 159 | 160 | 163 | 169 | 185 | 205 | 226 | 277 | 343 |
| Expected cost (uncalibrated) | 165 | 159 | 158 | 161 | 168 | 185 | 204 | 223 | 275 | 343 |
| Confidence only | 165 | 160 | 163 | 170 | 178 | 191 | 206 | 226 | 278 | 343 |
| Stake only | 165 | 172 | 178 | 186 | 193 | 207 | 222 | 239 | 281 | 343 |
| Random audit | 165 | 172 | 179 | 186 | 193 | 207 | 222 | 236 | 281 | 343 |

Configured policy: loss 166 [164, 167] per 1,000 with 21.9 [21.1, 22.6]% of cases to a human and 14.0 [13.2, 14.7] reviewer hours per 1,000.

At a matched 20% review share (expected cost, calibrated, minus each alternative; Holm-adjusted):

| Alternative router | Loss difference / 1,000 | 95% CI | p (Holm) |
|---|---|---|---|
| Expected cost (uncalibrated) | +0.9 | [+0.3, +1.5] | 0.011 |
| Confidence only | -8.3 | [-10.2, -6.5] | <0.001 |
| Stake only | -23.2 | [-25.3, -21.1] | <0.001 |
| Random audit | -23.3 | [-24.8, -21.9] | <0.001 |

### Payments (synthetic)

| Router | 0% | 5% | 10% | 15% | 20% | 30% | 40% | 50% | 75% | 100% |
|---|---|---|---|---|---|---|---|---|---|---|
| Expected cost (calibrated) | 239973 | 219416 | 215029 | 210791 | 207393 | 202707 | 199587 | 198338 | 198431 | 204535 |
| Expected cost (uncalibrated) | 239973 | 220641 | 215847 | 211320 | 207731 | 203069 | 200666 | 199283 | 199139 | 204535 |
| Confidence only | 239973 | 231745 | 232023 | 230041 | 224635 | 214278 | 206571 | 202078 | 199133 | 204535 |
| Stake only | 239973 | 221984 | 217624 | 212201 | 209614 | 205068 | 202528 | 199717 | 199200 | 204535 |
| Random audit | 239973 | 238307 | 235037 | 233408 | 230713 | 226093 | 220931 | 218634 | 208019 | 204535 |

Configured policy: loss 188883 [183726, 193965] per 1,000 with 23.5 [23.1, 23.9]% of cases to a human and 13.4 [13.1, 13.7] reviewer hours per 1,000.

At a matched 20% review share (expected cost, calibrated, minus each alternative; Holm-adjusted):

| Alternative router | Loss difference / 1,000 | 95% CI | p (Holm) |
|---|---|---|---|
| Expected cost (uncalibrated) | -338.1 | [-1169.5, +437.2] | 0.434 |
| Confidence only | -17242.2 | [-21976.0, -12603.8] | <0.001 |
| Stake only | -2221.9 | [-3792.0, -757.3] | 0.018 |
| Random audit | -23320.4 | [-28129.2, -18775.1] | <0.001 |

## E4: Sensitivity to reviewer assumptions

_Source: `results/e4_sensitivity/20261008T013352Z-cc94fe5` · commit `cc94fe5550b1` · 10 seeds from base 20261008 · runtime 946.1 s._

One parameter varies at a time; others stay at their defaults. Loss per 1,000 cases (mean over seeds). The last columns compare risk-adaptive oversight with the alternatives, paired over seeds (negative = adaptive loses less).

### `automation_bias_review`

| Domain | Value | Human only | AI only | AI + blanket approval | Risk-adaptive oversight | Lowest loss | Adaptive - AI only | Adaptive - blanket |
|---|---|---|---|---|---|---|---|---|
| credit | 0 | 1885711 | 1902416 | 1872020 | 1926682 | AI + blanket approval | +24266 (p 0.902) | +54662 (p 0.434) |
| credit | 0.25 | 1885711 | 1902416 | 1872020 | 1858298 | Risk-adaptive oversight | -44118 (p 0.735) | -13723 (p 0.818) |
| credit | 0.5 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| credit | 0.75 | 1885711 | 1902416 | 1872020 | 1969610 | AI + blanket approval | +67194 (p 0.555) | +97590 (p 0.354) |
| credit | 0.9 | 1885711 | 1902416 | 1872020 | 1912599 | AI + blanket approval | +10183 (p 0.927) | +40578 (p 0.685) |
| eligibility | 0 | 440 | 165 | 384 | 179 | AI only | +14 (p 0.001) | -205 (p 0.001) |
| eligibility | 0.25 | 440 | 165 | 384 | 173 | AI only | +8 (p 0.001) | -211 (p 0.001) |
| eligibility | 0.5 | 440 | 165 | 384 | 166 | AI only | +2 (p 0.330) | -218 (p 0.001) |
| eligibility | 0.75 | 440 | 165 | 384 | 159 | Risk-adaptive oversight | -6 (p 0.003) | -225 (p 0.001) |
| eligibility | 0.9 | 440 | 165 | 384 | 156 | Risk-adaptive oversight | -9 (p 0.001) | -228 (p 0.001) |
| payments | 0 | 148568 | 240314 | 164948 | 170430 | Human only | -69884 (p 0.001) | +5482 (p 0.013) |
| payments | 0.25 | 148568 | 240314 | 164948 | 177959 | Human only | -62355 (p 0.001) | +13011 (p 0.001) |
| payments | 0.5 | 148568 | 240314 | 164948 | 188286 | Human only | -52028 (p 0.001) | +23338 (p 0.001) |
| payments | 0.75 | 148568 | 240314 | 164948 | 194279 | Human only | -46035 (p 0.001) | +29331 (p 0.001) |
| payments | 0.9 | 148568 | 240314 | 164948 | 198783 | Human only | -41531 (p 0.001) | +33835 (p 0.001) |

### `acc_hard`

| Domain | Value | Human only | AI only | AI + blanket approval | Risk-adaptive oversight | Lowest loss | Adaptive - AI only | Adaptive - blanket |
|---|---|---|---|---|---|---|---|---|
| credit | 0.55 | 2312582 | 1902416 | 2199614 | 1892564 | Risk-adaptive oversight | -9852 (p 0.933) | -307050 (p 0.003) |
| credit | 0.65 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| credit | 0.75 | 1438524 | 1902416 | 1483168 | 1608548 | Human only | -293868 (p 0.017) | +125380 (p 0.085) |
| credit | 0.85 | 807862 | 1902416 | 1009208 | 1396143 | Human only | -506272 (p 0.003) | +386934 (p 0.001) |
| eligibility | 0.55 | 503 | 165 | 435 | 182 | AI only | +17 (p 0.001) | -253 (p 0.001) |
| eligibility | 0.65 | 440 | 165 | 384 | 166 | AI only | +2 (p 0.330) | -218 (p 0.001) |
| eligibility | 0.75 | 375 | 165 | 332 | 150 | Risk-adaptive oversight | -15 (p 0.001) | -182 (p 0.001) |
| eligibility | 0.85 | 310 | 165 | 280 | 133 | Risk-adaptive oversight | -32 (p 0.001) | -147 (p 0.001) |
| payments | 0.55 | 174641 | 240314 | 185905 | 200984 | Human only | -39330 (p 0.001) | +15079 (p 0.003) |
| payments | 0.65 | 148568 | 240314 | 164948 | 188286 | Human only | -52028 (p 0.001) | +23338 (p 0.001) |
| payments | 0.75 | 126656 | 240314 | 148040 | 177030 | Human only | -63284 (p 0.001) | +28990 (p 0.001) |
| payments | 0.85 | 101234 | 240314 | 127698 | 165734 | Human only | -74581 (p 0.001) | +38035 (p 0.001) |

### `minutes_review`

| Domain | Value | Human only | AI only | AI + blanket approval | Risk-adaptive oversight | Lowest loss | Adaptive - AI only | Adaptive - blanket |
|---|---|---|---|---|---|---|---|---|
| credit | 1 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| credit | 2 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| credit | 4 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| eligibility | 1 | 440 | 165 | 384 | 166 | AI only | +1 (p 0.338) | -218 (p 0.001) |
| eligibility | 2 | 440 | 165 | 384 | 166 | AI only | +2 (p 0.330) | -218 (p 0.001) |
| eligibility | 4 | 440 | 165 | 384 | 167 | AI only | +2 (p 0.292) | -218 (p 0.001) |
| payments | 1 | 148568 | 240314 | 164948 | 188286 | Human only | -52028 (p 0.001) | +23338 (p 0.001) |
| payments | 2 | 148568 | 240314 | 164948 | 188286 | Human only | -52028 (p 0.001) | +23338 (p 0.001) |
| payments | 4 | 148568 | 240314 | 164948 | 188319 | Human only | -51996 (p 0.001) | +23370 (p 0.001) |

### `reviewers`

| Domain | Value | Human only | AI only | AI + blanket approval | Risk-adaptive oversight | Lowest loss | Adaptive - AI only | Adaptive - blanket |
|---|---|---|---|---|---|---|---|---|
| credit | 2 | 1920220 | 1902416 | 1906530 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -105468 (p 0.194) |
| credit | 4 | 1885711 | 1902416 | 1872020 | 1801062 | Risk-adaptive oversight | -101353 (p 0.439) | -70958 (p 0.345) |
| credit | 8 | 1797970 | 1902416 | 1790584 | 1801062 | AI + blanket approval | -101353 (p 0.439) | +10478 (p 0.880) |
| eligibility | 2 | 446 | 165 | 389 | 167 | AI only | +2 (p 0.175) | -222 (p 0.001) |
| eligibility | 4 | 440 | 165 | 384 | 166 | AI only | +2 (p 0.330) | -218 (p 0.001) |
| eligibility | 8 | 357 | 165 | 318 | 166 | AI only | +1 (p 0.382) | -151 (p 0.001) |
| payments | 2 | 150533 | 240314 | 166525 | 188792 | Human only | -51523 (p 0.001) | +22267 (p 0.001) |
| payments | 4 | 148568 | 240314 | 164948 | 188286 | Human only | -52028 (p 0.001) | +23338 (p 0.001) |
| payments | 8 | 123711 | 240314 | 145412 | 188164 | Human only | -52150 (p 0.001) | +42752 (p 0.001) |

## E5: Distribution shift (synthetic payments)

_Source: `results/e5_shift/20261008T013559Z-cc94fe5` · commit `cc94fe5550b1` · 20 seeds from base 20261008 · runtime 123.1 s._

The agent, calibrator and policy are fitted before the shift; the test stream comes from the shifted generator.

### Covariate shift

| Level | AI accuracy (%) | Mean confidence (%) | ECE (pp) | Autonomous share (%) | Loss: Human only | Loss: AI only | Loss: AI + blanket approval | Loss: Risk-adaptive oversight | Reviewer h / 1,000 (adaptive) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 84.0 [83.3, 84.6] | 84.2 [83.5, 84.8] | 1.8 [1.7, 1.9] | 76.7 [76.2, 77.2] | 136200 [131510, 141216] | 224863 [214547, 235582] | 156772 [151686, 161988] | 179577 [174207, 185166] | 12.7 [12.4, 13.1] |
| 0.5 | 78.7 [77.7, 79.6] | 79.0 [77.9, 80.0] | 2.0 [1.8, 2.2] | 64.3 [63.7, 64.9] | 239365 [231660, 247036] | 340571 [330293, 350905] | 259837 [251950, 267824] | 274787 [267065, 281944] | 21.3 [20.8, 21.9] |
| 1 | 73.4 [72.0, 74.7] | 73.6 [72.0, 75.1] | 2.7 [2.4, 2.9] | 51.2 [50.6, 51.9] | 390755 [377702, 404443] | 514920 [502449, 527174] | 415908 [407576, 424457] | 411074 [402021, 420094] | 32.2 [31.6, 32.7] |

### Concept shift

| Level | AI accuracy (%) | Mean confidence (%) | ECE (pp) | Autonomous share (%) | Loss: Human only | Loss: AI only | Loss: AI + blanket approval | Loss: Risk-adaptive oversight | Reviewer h / 1,000 (adaptive) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 83.9 [83.1, 84.5] | 84.3 [83.6, 84.9] | 1.7 [1.6, 1.8] | 76.8 [76.4, 77.3] | 143191 [137072, 149315] | 230092 [221198, 239132] | 164795 [158706, 171672] | 187269 [180064, 194831] | 12.7 [12.4, 13.1] |
| 0.5 | 84.4 [83.7, 84.9] | 84.3 [83.5, 84.9] | 2.1 [1.8, 2.3] | 76.8 [76.3, 77.3] | 141978 [135346, 149340] | 225487 [218934, 232005] | 157956 [150669, 165862] | 181947 [175326, 189314] | 12.9 [12.5, 13.2] |
| 1 | 84.7 [84.2, 85.1] | 84.1 [83.4, 84.7] | 2.8 [2.6, 3.0] | 76.6 [76.2, 77.0] | 152089 [146732, 158087] | 235679 [224263, 247831] | 167976 [161430, 175255] | 189718 [181862, 197555] | 13.1 [12.8, 13.3] |

## Human-subject study

Status: pending. Trust and reviewer behaviour above come from a simulated reviewer with stated parameters; no study with real reviewers has been run (see docs/PLAN.md).

