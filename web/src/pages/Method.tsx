import { Link } from "react-router-dom";
import { ErrorPanel, Loading, PageHead } from "../components/ui";
import { api, useApi, type E2Summary } from "../lib/api";

const PARAM_TEXT: Record<string, string> = {
  acc_easy: "Probability a reviewer judges an easy case correctly",
  acc_hard: "Probability a reviewer judges the hardest case correctly (linear in difficulty between the two)",
  review_accuracy_penalty: "Accuracy lost when reviewing someone else's decision rather than deciding",
  automation_bias_review: "Probability of deferring to the AI without judging, in review mode",
  automation_bias_approval: "Probability of deferring to the AI without judging, in mandatory approval",
  minutes_unaided: "Median minutes to decide a case without the AI",
  minutes_review: "Median minutes to review an AI decision",
  minutes_approval: "Median minutes for a mandatory approval",
  time_sigma: "Log-normal spread of handling time",
  difficulty_time_factor: "Extra handling time on the hardest cases (fraction)",
  fatigue_per_busy_hour: "Accuracy lost per continuous busy hour",
  fatigue_cap: "Maximum accuracy lost to fatigue",
  fatigue_reset_idle_minutes: "Idle minutes that reset fatigue",
  reviewers: "Reviewers on shift",
  arrivals_per_hour: "Cases arriving per hour",
};

export function Method() {
  const s = useApi<E2Summary>(api.experiment("e2_regimes"));
  const prov = s.data?.provenance;
  return (
    <>
      <PageHead title="Method">How the console decides who decides, what the experiments measure, and what they cannot tell you.</PageHead>
      <div className="grid two">
        <article className="panel prose" aria-labelledby="flow-title">
          <div className="panel-head">
            <h2 id="flow-title" style={{ margin: 0 }}>
              Decision flow
            </h2>
          </div>
          <div className="panel-body">
            <ol>
              <li>
                <strong>Agent decision.</strong> A model scores each case; the action is chosen by the Bayes threshold implied by the domain's two error costs.
              </li>
              <li>
                <strong>Calibrated confidence.</strong> A calibrator fitted on a held-out split turns the score into the probability that the chosen action is correct (see{" "}
                <Link to="/calibration">Calibration</Link>).
              </li>
              <li>
                <strong>Risk assessment.</strong> Expected cost = (1 − confidence) × cost if wrong, which grows with the stake and with doubt.
              </li>
              <li>
                <strong>Route.</strong> The policy maps expected cost to autonomous, review or mandatory approval; hard rules can only raise the tier (see{" "}
                <Link to="/policy">Policy</Link>). Every route is logged with the policy hash (see <Link to="/audit">Audit</Link>).
              </li>
            </ol>
            <h2>The four regimes compared</h2>
            <ul>
              <li>
                <strong>Human only:</strong> a person decides every case without seeing the AI.
              </li>
              <li>
                <strong>AI only:</strong> every AI decision executes.
              </li>
              <li>
                <strong>AI + blanket approval:</strong> every AI decision waits for a person's approval.
              </li>
              <li>
                <strong>Risk-adaptive:</strong> the policy above.
              </li>
            </ul>
            <h2>Metrics</h2>
            <ul>
              <li>Loss: cost of wrong final decisions per 1,000 cases, in the domain's stake units. The primary outcome, since the costs are asymmetric.</li>
              <li>Accuracy and error rate of final decisions; error attribution to autonomous AI errors, accepted wrong AI decisions, harmful overrides and unaided human errors.</li>
              <li>Human workload: share of cases a person touches and reviewer hours per 1,000 cases.</li>
              <li>Decision time: arrival to final decision through a staffed queue, median and 95th percentile.</li>
              <li>Override rate and precision; automation bias (accepting a wrong AI decision); appropriate reliance.</li>
              <li>Calibration: ECE, Brier score and NLL on the test stream.</li>
            </ul>
          </div>
        </article>
        <article className="panel prose" aria-labelledby="lim-title">
          <div className="panel-head">
            <h2 id="lim-title" style={{ margin: 0 }}>
              Limits of the evidence
            </h2>
          </div>
          <div className="panel-body">
            <ul>
              <li>
                <strong>Reviewers are simulated.</strong> Their accuracy, deference and speed are stated parameters, not measurements. E4 varies them one at a time to show which
                conclusions depend on them.
              </li>
              <li>
                <strong>Trust is measured by proxy.</strong> Override rate, override precision, automation bias and appropriate reliance describe simulated behaviour. A study with
                real reviewers is <strong>Status: pending</strong>.
              </li>
              <li>
                <strong>Costs are partly assumed.</strong> German Credit's 5:1 cost matrix is the dataset's own; the eligibility and payment costs are assumptions stated in the
                dataset card.
              </li>
              <li>
                <strong>Eligibility is a stand-in.</strong> The Adult label is 1994 census income, framed as programme eligibility; groups are reported for error analysis only.
              </li>
              <li>
                <strong>Credit is small.</strong> 200 test cases per seed with stakes up to 18,424 DM make loss estimates noisy; most credit loss differences are not significant.
              </li>
            </ul>
            <h2>Reviewer model used in E2</h2>
            {s.error && !s.data ? (
              <ErrorPanel error={s.error} retry={s.retry} what="the reviewer parameters" />
            ) : !prov ? (
              <Loading rows={4} label="Loading parameters" />
            ) : (
              <div className="table-wrap" tabIndex={0}>
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Parameter</th>
                      <th scope="col">Meaning</th>
                      <th scope="col" className="r">
                        Value
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries({ ...prov.reviewer, ...prov.staffing }).map(([k, v]) => (
                      <tr key={k}>
                        <td className="mono">{k}</td>
                        <td className="secondary">{PARAM_TEXT[k] ?? ""}</td>
                        <td className="r">{String(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </article>
      </div>
    </>
  );
}
