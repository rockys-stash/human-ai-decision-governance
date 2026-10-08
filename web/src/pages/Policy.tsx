import { useSearchParams } from "react-router-dom";
import { LineChart, TableTwin } from "../components/charts";
import { ErrorPanel, Loading, PageHead, ProvenanceLine, Segmented, TierBadge } from "../components/ui";
import { api, useApi, type Domain, type E2Summary, type E3Summary, type PolicyDoc } from "../lib/api";
import { aggText, compact, DOMAIN_LABEL, DOMAINS, pct, ROUTER_COLOR, ROUTER_LABEL, ROUTERS } from "../lib/format";

const OP: Record<string, string> = { gt: ">", gte: "≥", lt: "<", lte: "≤", eq: "=", in: "in" };

export function useDomainParam(): [Domain, (d: Domain) => void] {
  const [params, setParams] = useSearchParams();
  const raw = params.get("domain");
  const domain = (DOMAINS as string[]).includes(raw ?? "") ? (raw as Domain) : "payments";
  const set = (d: Domain) => {
    const next = new URLSearchParams(params);
    next.set("domain", d);
    setParams(next, { replace: true });
  };
  return [domain, set];
}

export function DomainPicker({ domain, onChange }: { domain: Domain; onChange: (d: Domain) => void }) {
  return <Segmented label="Domain" options={DOMAINS.map((d) => ({ id: d, label: DOMAIN_LABEL[d] }))} value={domain} onChange={onChange} />;
}

export function Policy() {
  const [domain, setDomain] = useDomainParam();
  const policies = useApi<PolicyDoc[]>(api.policies);
  const e2 = useApi<E2Summary>(api.experiment("e2_regimes"));
  const e3 = useApi<E3Summary>(api.experiment("e3_frontier"));
  const p = policies.data?.find((x) => x.domain === domain);
  const ra = e2.data?.domains[domain]?.regimes.risk_adaptive;
  const fr = e3.data?.domains[domain];

  return (
    <>
      <PageHead title="Policy" actions={<DomainPicker domain={domain} onChange={setDomain} />}>
        The rulebook that routes each AI decision. Two expected-cost thresholds grade risk; hard rules can raise a case's tier but never lower it. The hash is written into every
        routing record.
      </PageHead>
      {policies.loading && !policies.data ? (
        <Loading rows={6} label="Loading policy" />
      ) : policies.error && !policies.data ? (
        <ErrorPanel error={policies.error} retry={policies.retry} what="policies" />
      ) : p ? (
        <div className="grid two">
          <section className="panel" aria-labelledby="pol-title">
            <div className="panel-head">
              <h2 id="pol-title">
                <code>{p.id}</code> v{p.version}
              </h2>
              <span className="muted">
                hash <code>{p.hash}</code>
              </span>
            </div>
            <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <p className="secondary" style={{ margin: 0 }}>
                {p.description}. Source <code>{p.path}</code>.
              </p>
              <div className="table-wrap" tabIndex={0}>
                <table>
                  <caption className="skip-link">Expected-cost thresholds</caption>
                  <thead>
                    <tr>
                      <th scope="col">Expected cost of executing the AI decision</th>
                      <th scope="col">Route</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="num">below {p.thresholds.review}</td>
                      <td>
                        <TierBadge tier="autonomous" />
                      </td>
                    </tr>
                    <tr>
                      <td className="num">
                        {p.thresholds.review} to below {p.thresholds.approval}
                      </td>
                      <td>
                        <TierBadge tier="review" />
                      </td>
                    </tr>
                    <tr>
                      <td className="num">{p.thresholds.approval} or more</td>
                      <td>
                        <TierBadge tier="approval" />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div>
                <h3 style={{ marginBottom: 8 }}>Hard rules</h3>
                {p.rules.length === 0 ? (
                  <p className="muted">None.</p>
                ) : (
                  <div className="table-wrap" tabIndex={0}>
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Rule</th>
                          <th scope="col">When</th>
                          <th scope="col">At least</th>
                          <th scope="col" className="r">
                            Fired (E2)
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {p.rules.map((r) => (
                          <tr key={r.id}>
                            <td>
                              <code>{r.id}</code>
                              <br />
                              <span className="muted">{r.description}</span>
                            </td>
                            <td className="mono">
                              {r.when.map((c, i) => (
                                <div key={i}>
                                  {c.field.replace("feature:", "")} {OP[c.op] ?? c.op} {JSON.stringify(c.value)}
                                </div>
                              ))}
                            </td>
                            <td>
                              <TierBadge tier={r.route} />
                            </td>
                            <td className="r">{ra?.rules_fired_share?.[r.id] !== undefined ? pct(ra.rules_fired_share[r.id]) : "n/a"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
            {ra?.tier_share && (
              <div className="panel-note">
                Measured in E2 (test streams, 20 seeds): autonomous {aggText(ra.tier_share.autonomous, (v) => pct(v))}, review {aggText(ra.tier_share.review, (v) => pct(v))},
                approval {aggText(ra.tier_share.approval, (v) => pct(v))}.
              </div>
            )}
          </section>
          <section className="panel" aria-labelledby="op-title">
            <div className="panel-head">
              <h2 id="op-title">Operating point on the measured frontier</h2>
            </div>
            <div className="panel-body">
              {e3.error && !e3.data ? (
                <ErrorPanel error={e3.error} retry={e3.retry} what="the frontier (E3)" />
              ) : !fr ? (
                <Loading rows={4} label="Loading frontier" />
              ) : (
                <>
                  <LineChart
                    ariaLabel={`Loss against share of cases sent to review for each routing score in ${DOMAIN_LABEL[domain]}, with the configured policy marked`}
                    series={ROUTERS.map((r) => ({
                      key: r,
                      name: ROUTER_LABEL[r] ?? r,
                      color: ROUTER_COLOR[r] ?? "var(--ref)",
                      dashed: r === "random",
                      points: (fr.curves[r] ?? []).map((pt) => ({ x: pt.share_human.mean ?? pt.target_share, y: pt.loss_per_1000.mean ?? 0 })),
                    }))}
                    markers={[{ key: "policy", name: "this policy", x: fr.policy.share_human.mean ?? 0, y: fr.policy.loss_per_1000.mean ?? 0, color: "var(--accent)" }]}
                    xLabel="share of cases sent to a human"
                    yLabel="loss per 1,000 cases"
                    formatX={(v) => `${Math.round(v * 100)}%`}
                    formatY={compact}
                    xDomain={[0, 1]}
                  />
                  <TableTwin
                    caption="Frontier: loss per 1,000 by routing score and review share"
                    head={["Router", ...(fr.curves.expected_cost ?? []).map((pt) => `${Math.round(pt.target_share * 100)}%`)]}
                    rows={ROUTERS.map((r) => [ROUTER_LABEL[r] ?? r, ...(fr.curves[r] ?? []).map((pt) => compact(pt.loss_per_1000.mean))])}
                  />
                  <p className="secondary" style={{ marginTop: 12 }}>
                    The policy sends {aggText(fr.policy.share_human, (v) => pct(v))} of cases to a person for a loss of {aggText(fr.policy.loss_per_1000, compact)} per 1,000.
                    Curves send the top share by each score to review only; the policy also uses mandatory approval, which reviewers defer to less.
                  </p>
                  {e3.data && <ProvenanceLine p={e3.data.provenance} />}
                </>
              )}
            </div>
          </section>
        </div>
      ) : (
        <ErrorPanel error={{ name: "Error", message: `no policy for ${domain}`, url: api.policies, status: 404 }} retry={policies.retry} what="the policy" />
      )}
    </>
  );
}
