# Design — "Decision Console"

## Visual concept

An operations control console for AI decisions. The operator's question is always *"what is the system deciding on its own right now, what is waiting for a human, and is the policy doing its job?"* The interface behaves like a dispatch console: a live queue is the centre of gravity, every case shows the route it took and why, and the policy that produced the route is one click away with its version hash. Dense but calm: graphite surfaces, one violet accent for interactive focus, and a reserved three-step risk scale that always pairs color with a shape and a word.

| Console element | Interface element |
|---|---|
| Dispatch board | Review queue: medium-risk (review) and high-risk (approval) cases with SLA timers |
| Case card | Case inspector: AI recommendation, calibrated confidence, expected cost, rules fired, feature evidence, decision controls |
| Rulebook | Policy view: thresholds and hard rules, version hash, projected workload / loss at each threshold |
| Flight recorder | Audit log: every routing decision with scores, rules and policy hash |
| Test range | Experiments: regime comparison, frontier, calibration, sensitivity, shift |

## Information architecture

```
Queue        /queue                 live review + approval queue (default view) · case inspector · accept / override
Audit        /audit                 routing log, filter by tier / rule / outcome
Policy       /policy                active policy, thresholds, rules, what-if over the measured frontier
Experiments  /experiments           E2 regimes · E3 frontier and ablations · E4 sensitivity · E5 shift
Calibration  /calibration           E1 reliability diagrams and calibration metrics per domain
Method       /method                reviewer model assumptions, metrics, limitations, pending human study
```

Primary interaction: open the next case in the queue, read why it was routed to a human, decide (accept or override, with a reason), see the next case. Secondary: compare oversight regimes and inspect the policy's operating point on the workload-loss frontier.

## Navigation model

Top bar with product mark, domain selector, live counters (pending review, pending approval, oldest wait) and reviewer sign-in status. Section tabs below the bar on all sizes (a console has few sections, so no side rail). Queue view is a two-pane master/detail on desktop; on mobile the list and the inspector are separate screens with a back control. Every case, experiment and policy view is URL-addressable.

## Typography

- Geist (400/500/600) for interface text and figures; Geist Mono (400/500) for case ids, hashes, timestamps, amounts in tables, policy YAML.
- Scale (px): 12 / 13 / 14 (body) / 16 / 20 / 24. Tight line height (1.4) for dense tables, 1.5 for prose.
- Tabular numerals in all numeric columns and counters.

## Color system (tokens)

Dark-first graphite; a light theme is provided and follows the OS unless the operator picks one.

| Token | Dark | Light | Use |
|---|---|---|---|
| `--page` | `#0f1012` | `#f4f4f5` | page plane |
| `--surface` | `#17181b` | `#ffffff` | panels, tables |
| `--surface-2` | `#1f2024` | `#f0f0f2` | headers, inputs, code |
| `--ink` | `#f2f2f3` | `#0e0f11` | primary text |
| `--ink-2` | `#b9bbc1` | `#45474d` | secondary text |
| `--ink-3` | `#8d9098` | `#62656c` | muted labels (AA on surface) |
| `--rule` | `#2a2b30` | `#e2e3e6` | hairlines |
| `--accent` | `#9085e9` | `#4a3aa7` | focus, selection, primary action, links |
| `--risk-low` | `#0ca30c` ● | `#0ca30c` ● | autonomous tier (status "good") |
| `--risk-medium` | `#fab219` ▲ | `#fab219` ▲ | review tier (status "warning") |
| `--risk-high` | `#d03b3b` ■ | `#d03b3b` ■ | approval tier (status "critical") |
| series 1–4 | `#3987e5` `#d95926` `#199e70` `#c98500` | `#2a78d6` `#eb6834` `#1baf7a` `#eda100` | the four regimes, fixed order: human-only, AI-only, blanket approval, risk-adaptive |

Risk colors are the reserved status palette and never carry meaning alone: each tier has a shape (● ▲ ■) and a text label. Regime colors follow a fixed order and never change when a regime is filtered out.

## Spacing and layout

4px base; scale 4 / 8 / 12 / 16 / 24 / 32. Content max width 1360px. Panels with 1px hairlines and 8px radius; no shadows in dark mode, a 1px rule in light mode.

## Component language

Dense tables with sticky headers; tier badges (shape + word); key-value inspectors; segmented controls for domain and regime selection; a single filled primary action per screen (the reviewer's decision). Destructive or irreversible actions are not present in this product; overriding the AI requires a reason.

## Data visualization

- Regime comparison: dot + 95% interval per regime and metric, regimes in fixed color order, values printed.
- Frontier: workload (x) vs cost-weighted loss (y), the risk-adaptive sweep as a line with markers, baselines as labeled points, the active policy highlighted.
- Reliability diagram: predicted confidence vs observed accuracy with the identity line and bin counts as a histogram strip.
- Sensitivity: small multiples, one per parameter, same y-axis.
- Every chart has a table twin and hover/focus tooltips; no dual axes.

## Motion

Only functional: queue rows animate in (150ms fade) when new cases arrive; panel transitions 120ms; all disabled under `prefers-reduced-motion`.

## Loading, empty and error states

- Loading: skeletons with final dimensions; refetches keep the previous data dimmed.
- Empty queue: "No cases waiting" with the counts of cases handled autonomously since the session started.
- Not signed in: queue is visible read-only with a sign-in panel explaining that decisions need a reviewer token.
- Error: inline panel naming the failing request and a retry button.

## Responsive behaviour

Breakpoints 640px and 1024px. Below 1024px the queue becomes list → detail navigation; tables scroll inside their panel; charts keep a minimum readable height.

## Accessibility

Landmarks, one h1 per view, labelled controls, visible 2px focus rings in the accent color, keyboard shortcuts in the queue (j/k move, a accept, o override, with an on-screen legend and no single-key action firing while typing), live region announcing new cases and submitted decisions, WCAG AA contrast in both themes, axe-core audit in CI.
