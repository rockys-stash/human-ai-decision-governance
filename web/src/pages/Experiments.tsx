import { useSearchParams } from "react-router-dom";
import { IntervalRows, LineChart, TableTwin } from "../components/charts";
import { ErrorPanel, Loading, PageHead, Pending, ProvenanceLine, Segmented } from "../components/ui";
import { api, useApi, type Agg, type Domain, type E2Summary, type E3Summary, type E4Summary, type E5Summary, type ExperimentInfo, type Regime } from "../lib/api";
import { aggText, compact, DOMAIN_LABEL, num, pct, REGIME_COLOR, REGIME_LABEL, REGIMES, ROUTER_COLOR, ROUTER_LABEL, ROUTERS } from "../lib/format";
import { DomainPicker, useDomainParam } from "./Policy";

type Tab = "e2_regimes" | "e3_frontier" | "e4_sensitivity" | "e5_shift";
const TABS: { id: Tab; label: string }[] = [
  { id: "e2_regimes", label: "E2 Regimes" },
  { id: "e3_frontier", label: "E3 Frontier" },
  { id: "e4_sensitivity", label: "E4 Sensitivity" },
  { id: "e5_shift", label: "E5 Shift" },
];

function pValue(p: number | undefined): string {
  if (p === undefined) return "n/a";
  return p < 0.001 ? "<0.001" : p.toFixed(3);
}

export function Experiments() {
  const [params, setParams] = useSearchParams();
  const tab = (TABS.find((t) => t.id === params.get("exp"))?.id ?? "e2_regimes") as Tab;
  const [domain, setDomain] = useDomainParam();
  const exps = useApi<ExperimentInfo[]>(api.experiments);
  const info = exps.data?.find((e) => e.experiment === tab);
  const setTab = (t: Tab) => {
    const next = new URLSearchParams(params);
    next.set("exp", t);
    setParams(next, { replace: true });
  };
  return (
    <>
      <PageHead
        title="Experiments"
        actions={
          <div className="toolbar" style={{ margin: 0 }}>
            <Segmented label="Experiment" options={TABS} value={tab} onChange={setTab} />
            {tab !== "e5_shift" && <DomainPicker domain={domain} onChange={setDomain} />}
          </div>
        }
      >
        Simulated comparisons of oversight regimes on held-out decision streams. Reviewer behaviour is a stated model, not measured people; see Method.
      </PageHead>
      {exps.error && !exps.data ? (
        <ErrorPanel error={exps.error} retry={exps.retry} what="the experiment list" />
      ) : !exps.data ? (
        <Loading rows={6} label="Loading experiments" />
      ) : info?.status !== "complete" ? (
        <Pending what={tab} />
      ) : tab === "e2_regimes" ? (
        <Regimes domain={domain} />
      ) : tab === "e3_frontier" ? (
        <Frontier domain={domain} />
      ) : tab === "e4_sensitivity" ? (
        <Sensitivity domain={domain} />
      ) : (
        <Shift />
      )}
    </>
  );
}

function regimeRows(get: (g: Regime) => Agg | undefined) {
  return REGIMES.map((g) => ({ key: g, label: REGIME_LABEL[g], color: REGIME_COLOR[g], stat: get(g) }));
}

function Regimes({ domain }: { domain: Domain }) {
  const s = useApi<E2Summary>(api.experiment("e2_regimes"));
  if (s.error && !s.data) return <ErrorPanel error={s.error} retry={s.retry} what="E2" />;
  if (!s.data) return <Loading rows={6} label="Loading E2" />;
  const d = s.data.domains[domain];
  if (!d) return <Pending what="e2_regimes" />;
  const r = d.regimes;
  const lossPairs = d.pairwise.filter((p) => p.metric === "loss_per_1000" && (p.a === "risk_adaptive" || p.b === "risk_adaptive"));
  return (
    <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>
      <section className="panel" aria-labelledby="e2-title">
        <div className="panel-head">
          <h2 id="e2-title">Four regimes in {DOMAIN_LABEL[domain]}: mean and 95% CI over seeds</h2>
          <div className="legend">
            {REGIMES.map((g) => (
              <span className="key" key={g}>
                <span className="swatch" style={{ background: REGIME_COLOR[g] }} />
                {REGIME_LABEL[g]}
              </span>
            ))}
          </div>
        </div>
        <div className="panel-body interval-grid">
          <IntervalRows title="Loss per 1,000 cases" better="lower" rows={regimeRows((g) => r[g]?.loss_per_1000)} format={compact} />
          <IntervalRows title="Accuracy" better="higher" rows={regimeRows((g) => r[g]?.accuracy)} format={(v) => pct(v)} />
          <IntervalRows title="Reviewer hours per 1,000 cases" better="lower" rows={regimeRows((g) => r[g]?.reviewer_hours_per_1000)} format={(v) => num(v, 1)} />
          <IntervalRows title="Decision time p95 (minutes)" better="lower" rows={regimeRows((g) => r[g]?.decision_minutes_p95)} format={(v) => num(v, 1)} />
          <IntervalRows title="Share of cases to a person" rows={regimeRows((g) => r[g]?.share_human)} format={(v) => pct(v, 0)} />
          <IntervalRows title="Override rate (shown cases)" rows={regimeRows((g) => r[g]?.override_rate)} format={(v) => pct(v)} />
        </div>
        <div className="panel-note">
          <ProvenanceLine p={s.data.provenance} />
        </div>
      </section>
      <div className="grid two">
        <section className="panel" aria-labelledby="attr-title">
          <div className="panel-head">
            <h2 id="attr-title">Where the errors come from (per 1,000 cases)</h2>
          </div>
          <div className="table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Regime</th>
                  <th scope="col" className="r">
                    Autonomous AI error
                  </th>
                  <th scope="col" className="r">
                    Accepted wrong AI
                  </th>
                  <th scope="col" className="r">
                    Harmful override
                  </th>
                  <th scope="col" className="r">
                    Unaided human error
                  </th>
                </tr>
              </thead>
              <tbody>
                {REGIMES.map((g) => {
                  const e = r[g]?.errors ?? {};
                  return (
                    <tr key={g}>
                      <th scope="row">{REGIME_LABEL[g]}</th>
                      {["autonomous_ai_error", "accepted_wrong_ai", "harmful_override", "unaided_human_error"].map((k) => (
                        <td key={k} className="r">
                          {num(e[k]?.mean, 1)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="panel-note">
            Reliance on cases where a person saw the AI's decision: automation bias {aggText(r.risk_adaptive?.automation_bias_rate, (v) => pct(v))} (risk-adaptive) vs{" "}
            {aggText(r.blanket_approval?.automation_bias_rate, (v) => pct(v))} (blanket approval). Override precision {aggText(r.risk_adaptive?.override_precision, (v) => pct(v))} vs{" "}
            {aggText(r.blanket_approval?.override_precision, (v) => pct(v))}.
          </div>
        </section>
        <section className="panel" aria-labelledby="pairs-title">
          <div className="panel-head">
            <h2 id="pairs-title">Is risk-adaptive loss different? (paired over seeds)</h2>
          </div>
          <div className="table-wrap" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  <th scope="col">Comparison</th>
                  <th scope="col" className="r">
                    Difference in loss / 1,000
                  </th>
                  <th scope="col" className="r">
                    95% CI
                  </th>
                  <th scope="col" className="r">
                    p (Holm)
                  </th>
                </tr>
              </thead>
              <tbody>
                {lossPairs.map((p) => {
                  const flip = p.b === "risk_adaptive";
                  const other = (flip ? p.a : p.b) as Regime;
                  const k = flip ? -1 : 1;
                  const lo = (flip ? p.ci_high : p.ci_low) ?? 0;
                  const hi = (flip ? p.ci_low : p.ci_high) ?? 0;
                  return (
                    <tr key={`${p.a}-${p.b}`}>
                      <th scope="row">Risk-adaptive − {REGIME_LABEL[other]}</th>
                      <td className="r">{compact((p.diff ?? 0) * k)}</td>
                      <td className="r">
                        [{compact(lo * k)}, {compact(hi * k)}]
                      </td>
                      <td className="r">{pValue(p.p_holm)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="panel-note">Negative means risk-adaptive oversight loses less. Two-sided sign-flip test over seeds, Holm-adjusted within the domain.</div>
        </section>
      </div>
    </div>
  );
}

function Frontier({ domain }: { domain: Domain }) {
  const s = useApi<E3Summary>(api.experiment("e3_frontier"));
  if (s.error && !s.data) return <ErrorPanel error={s.error} retry={s.retry} what="E3" />;
  if (!s.data) return <Loading rows={6} label="Loading E3" />;
  const d = s.data.domains[domain];
  if (!d) return <Pending what="e3_frontier" />;
  return (
    <div className="grid two">
      <section className="panel" aria-labelledby="e3-title">
        <div className="panel-head">
          <h2 id="e3-title">Loss vs share sent to review, by routing score</h2>
        </div>
        <div className="panel-body">
          <LineChart
            ariaLabel={`Frontier of loss against review share in ${DOMAIN_LABEL[domain]}`}
            series={ROUTERS.map((r) => ({
              key: r,
              name: ROUTER_LABEL[r] ?? r,
              color: ROUTER_COLOR[r] ?? "var(--ref)",
              dashed: r === "random",
              points: (d.curves[r] ?? []).map((pt) => ({
                x: pt.share_human.mean ?? pt.target_share,
                y: pt.loss_per_1000.mean ?? 0,
                lo: r === "expected_cost" ? pt.loss_per_1000.ci_low : null,
                hi: r === "expected_cost" ? pt.loss_per_1000.ci_high : null,
              })),
            }))}
            markers={[{ key: "policy", name: "configured policy", x: d.policy.share_human.mean ?? 0, y: d.policy.loss_per_1000.mean ?? 0, color: "var(--accent)" }]}
            xLabel="share of cases sent to a human"
            yLabel="loss per 1,000 cases"
            formatX={(v) => `${Math.round(v * 100)}%`}
            formatY={compact}
            xDomain={[0, 1]}
            height={300}
          />
          <TableTwin
            caption="Loss per 1,000 by router and review share"
            head={["Router", ...(d.curves.expected_cost ?? []).map((pt) => `${Math.round(pt.target_share * 100)}%`)]}
            rows={ROUTERS.map((r) => [ROUTER_LABEL[r] ?? r, ...(d.curves[r] ?? []).map((pt) => compact(pt.loss_per_1000.mean))])}
          />
        </div>
        <div className="panel-note">
          <ProvenanceLine p={s.data.provenance} />
        </div>
      </section>
      <section className="panel" aria-labelledby="matched-title">
        <div className="panel-head">
          <h2 id="matched-title">At a matched {Math.round(s.data.matched_share * 100)}% review share</h2>
        </div>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">Calibrated expected cost minus</th>
                <th scope="col" className="r">
                  Loss / 1,000
                </th>
                <th scope="col" className="r">
                  95% CI
                </th>
                <th scope="col" className="r">
                  p (Holm)
                </th>
              </tr>
            </thead>
            <tbody>
              {d.matched.map((p) => (
                <tr key={p.b}>
                  <th scope="row">{ROUTER_LABEL[p.b] ?? p.b}</th>
                  <td className="r">{compact(p.diff)}</td>
                  <td className="r">
                    [{compact(p.ci_low)}, {compact(p.ci_high)}]
                  </td>
                  <td className="r">{pValue(p.p_holm)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel-note">
          Negative means routing by calibrated expected cost loses less than the alternative at the same human workload. Thresholds for every router come from the calibration
          split, never the test stream.
        </div>
      </section>
    </div>
  );
}

const AXIS_LABEL: Record<string, string> = {
  automation_bias_review: "Deference to the AI in review",
  acc_hard: "Reviewer accuracy on the hardest cases",
  minutes_review: "Minutes per review",
  reviewers: "Reviewers on shift",
};

function RegimeLegend() {
  return (
    <div className="legend">
      {REGIMES.map((g) => (
        <span className="key" key={g}>
          <span className="swatch line" style={{ background: REGIME_COLOR[g] }} />
          {REGIME_LABEL[g]}
        </span>
      ))}
    </div>
  );
}

function Sensitivity({ domain }: { domain: Domain }) {
  const s = useApi<E4Summary>(api.experiment("e4_sensitivity"));
  if (s.error && !s.data) return <ErrorPanel error={s.error} retry={s.retry} what="E4" />;
  if (!s.data) return <Loading rows={6} label="Loading E4" />;
  const axes = Object.entries(s.data.axes);
  const loss = (row: Record<string, unknown>, g: Regime) => (row[g] as { loss_per_1000: Agg } | undefined)?.loss_per_1000;
  // One shared y-axis across the small multiples, so panels compare directly.
  const all = axes.flatMap(([, per]) => (per[domain] ?? []).flatMap((row) => REGIMES.flatMap((g) => [loss(row, g)?.ci_low, loss(row, g)?.ci_high]))).filter((v): v is number => typeof v === "number");
  const pad = (Math.max(...all) - Math.min(...all)) * 0.06;
  const yDomain: [number, number] = [Math.max(0, Math.min(...all) - pad), Math.max(...all) + pad];
  return (
    <section className="panel" aria-labelledby="e4-title">
      <div className="panel-head">
        <h2 id="e4-title">Loss per 1,000 as one reviewer assumption varies ({DOMAIN_LABEL[domain]})</h2>
        <RegimeLegend />
      </div>
      <div className="panel-body small-multiples wide">
        {axes.map(([param, per]) => {
          const rows = per[domain] ?? [];
          return (
            <figure key={param} style={{ margin: 0 }}>
              <figcaption style={{ fontWeight: 500, marginBottom: 4 }}>{AXIS_LABEL[param] ?? param}</figcaption>
              <LineChart
                ariaLabel={`Loss by regime as ${AXIS_LABEL[param] ?? param} varies`}
                series={REGIMES.map((g) => ({
                  key: g,
                  name: REGIME_LABEL[g],
                  color: REGIME_COLOR[g],
                  points: rows.map((row) => {
                    const st = loss(row, g);
                    return { x: row.value, y: st?.mean ?? 0, lo: st?.ci_low, hi: st?.ci_high };
                  }),
                }))}
                xLabel={param}
                yLabel="loss per 1,000"
                formatX={(v) => String(v)}
                formatY={compact}
                yDomain={yDomain}
                height={250}
                width={440}
                legend={false}
              />
              <TableTwin
                caption={`Lowest-loss regime by ${param}`}
                head={["Value", ...REGIMES.map((g) => REGIME_LABEL[g]), "Lowest loss", "Adaptive − AI only (p)"]}
                rows={rows.map((row) => {
                  const t = row.adaptive_vs_ai_only as { diff: number; p_value: number };
                  return [String(row.value), ...REGIMES.map((g) => compact(loss(row, g)?.mean)), REGIME_LABEL[row.lowest_loss_regime], `${compact(t.diff)} (${pValue(t.p_value)})`];
                })}
              />
            </figure>
          );
        })}
      </div>
      <div className="panel-note">
        Ten seeds per setting. Review speed changes reviewer hours and waiting time but not accuracy, so its loss lines are flat by construction.{" "}
        <ProvenanceLine p={s.data.provenance} />
      </div>
    </section>
  );
}

function Shift() {
  const s = useApi<E5Summary>(api.experiment("e5_shift"));
  if (s.error && !s.data) return <ErrorPanel error={s.error} retry={s.retry} what="E5" />;
  if (!s.data) return <Loading rows={6} label="Loading E5" />;
  const kinds = ["covariate", "concept"] as const;
  return (
    <section className="panel" aria-labelledby="e5-title">
      <div className="panel-head">
        <h2 id="e5-title">Synthetic payments after a distribution shift</h2>
        <RegimeLegend />
      </div>
      <div className="panel-body small-multiples wide">
        {kinds.map((kind) => {
          const rows = s.data?.shifts[kind] ?? [];
          return (
            <figure key={kind} style={{ margin: 0 }}>
              <figcaption style={{ fontWeight: 500, marginBottom: 4 }}>{kind === "covariate" ? "Covariate shift" : "Concept shift"}: loss per 1,000</figcaption>
              <LineChart
                ariaLabel={`Loss by regime under ${kind} shift`}
                series={REGIMES.map((g) => ({
                  key: g,
                  name: REGIME_LABEL[g],
                  color: REGIME_COLOR[g],
                  points: rows.map((row) => ({ x: row.level, y: (row[g] as { loss_per_1000: Agg }).loss_per_1000.mean ?? 0 })),
                }))}
                xLabel="shift level"
                yLabel="loss per 1,000"
                formatX={(v) => String(v)}
                formatY={compact}
                height={250}
                width={440}
                legend={false}
              />
              <TableTwin
                caption={`${kind} shift: calibration and routing`}
                head={["Level", "AI accuracy", "ECE", "Autonomous share"]}
                rows={rows.map((row) => [String(row.level), pct(row.ai_accuracy.mean), pct(row.ece.mean), pct(row.autonomous_share.mean)])}
              />
            </figure>
          );
        })}
      </div>
      <div className="panel-note">
        The agent, calibrator and policy were fitted before the shift. Under covariate shift the router sends more cases to people on its own as expected cost rises.{" "}
        <ProvenanceLine p={s.data.provenance} />
      </div>
    </section>
  );
}
