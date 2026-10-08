import { useState } from "react";
import { LineChart, TableTwin } from "../components/charts";
import { ErrorPanel, Loading, PageHead, Pending, ProvenanceLine, Segmented } from "../components/ui";
import { api, useApi, type E1Summary, type ExperimentInfo } from "../lib/api";
import { aggText, DOMAIN_LABEL, num, pct } from "../lib/format";
import { DomainPicker, useDomainParam } from "./Policy";

const CALS = ["none", "platt", "isotonic"] as const;
const CAL_LABEL: Record<string, string> = { none: "Uncalibrated", platt: "Platt", isotonic: "Isotonic" };
const CAL_COLOR: Record<string, string> = { none: "var(--s2)", platt: "var(--s3)", isotonic: "var(--s1)" };

export function Calibration() {
  const [domain, setDomain] = useDomainParam();
  const [model, setModel] = useState<"gbm" | "logreg">("gbm");
  const exps = useApi<ExperimentInfo[]>(api.experiments);
  const complete = exps.data?.find((e) => e.experiment === "e1_calibration")?.status === "complete";
  const s = useApi<E1Summary>(complete ? api.experiment("e1_calibration") : null);
  return (
    <>
      <PageHead
        title="Calibration"
        actions={
          <div className="toolbar" style={{ margin: 0 }}>
            <Segmented
              label="Model"
              options={[
                { id: "gbm", label: "Gradient boosting" },
                { id: "logreg", label: "Logistic regression" },
              ]}
              value={model}
              onChange={setModel}
            />
            <DomainPicker domain={domain} onChange={setDomain} />
          </div>
        }
      >
        The router trusts the agent's confidence, so confidence has to mean what it says: among decisions made at 80% confidence, about 80% should be right. Calibrators are
        fitted on a held-out calibration split; everything here is on the test stream.
      </PageHead>
      {exps.error && !exps.data ? (
        <ErrorPanel error={exps.error} retry={exps.retry} what="the experiment list" />
      ) : exps.data && !complete ? (
        <Pending what="e1_calibration" />
      ) : s.error && !s.data ? (
        <ErrorPanel error={s.error} retry={s.retry} what="E1" />
      ) : !s.data ? (
        <Loading rows={6} label="Loading calibration results" />
      ) : (
        <div className="grid two">
          <section className="panel" aria-labelledby="rel-title">
            <div className="panel-head">
              <h2 id="rel-title">Reliability diagram, {DOMAIN_LABEL[domain]}</h2>
            </div>
            <div className="panel-body">
              <LineChart
                ariaLabel={`Observed accuracy against decision confidence for each calibrator in ${DOMAIN_LABEL[domain]}`}
                series={CALS.map((c) => ({
                  key: c,
                  name: CAL_LABEL[c] ?? c,
                  color: CAL_COLOR[c] ?? "var(--ref)",
                  points: (s.data?.reliability[`${domain}|${model}|${c}`] ?? []).map((b) => ({ x: b.conf, y: b.acc })),
                }))}
                identity
                xLabel="decision confidence (bin mean)"
                yLabel="observed accuracy"
                formatX={(v) => `${Math.round(v * 100)}%`}
                formatY={(v) => `${Math.round(v * 100)}%`}
                xDomain={[0.5, 1]}
                yDomain={[0.3, 1]}
                height={300}
              />
              <TableTwin
                caption="Reliability bins (pooled over seeds, 15 equal-mass bins)"
                head={["Calibrator", "Bin", "Confidence", "Accuracy", "Cases"]}
                rows={CALS.flatMap((c) =>
                  (s.data?.reliability[`${domain}|${model}|${c}`] ?? []).map((b, i) => [CAL_LABEL[c] ?? c, String(i + 1), pct(b.conf), pct(b.acc), num(b.count)]),
                )}
              />
              <p className="muted" style={{ fontSize: 12.5, marginTop: 8 }}>
                Points below the dashed line are over-confident. Bins hold equal numbers of cases, pooled over all seeds.
              </p>
            </div>
          </section>
          <section className="panel" aria-labelledby="cal-metrics">
            <div className="panel-head">
              <h2 id="cal-metrics">Calibration metrics (mean [95% CI] over seeds)</h2>
            </div>
            <div className="table-wrap" tabIndex={0}>
              <table>
                <thead>
                  <tr>
                    <th scope="col">Calibrator</th>
                    <th scope="col" className="r">
                      Accuracy
                    </th>
                    <th scope="col" className="r">
                      ECE
                    </th>
                    <th scope="col" className="r">
                      Brier
                    </th>
                    <th scope="col" className="r">
                      NLL
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {CALS.map((c) => {
                    const m = s.data?.by_condition[`${domain}|${model}|${c}`] ?? {};
                    return (
                      <tr key={c}>
                        <th scope="row">{CAL_LABEL[c]}</th>
                        <td className="r">{aggText(m.accuracy, (v) => pct(v))}</td>
                        <td className="r">{aggText(m.ece, (v) => pct(v))}</td>
                        <td className="r">{aggText(m.brier, (v) => num(v, 4))}</td>
                        <td className="r">{aggText(m.nll, (v) => num(v, 3))}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="panel-note">
              ECE: expected calibration error of the decision confidence, 15 equal-mass bins. Brier and NLL score the probability of the positive action.{" "}
              <ProvenanceLine p={s.data.provenance} />
            </div>
          </section>
        </div>
      )}
    </>
  );
}
