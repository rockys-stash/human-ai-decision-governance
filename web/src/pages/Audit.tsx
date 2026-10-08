import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorPanel, Empty, Loading, PageHead } from "../components/ui";
import { api, getJson, useApi, type AuditEvent } from "../lib/api";
import { useLive } from "../lib/live";

interface Verify {
  valid: boolean;
  events: number;
  head?: string;
  first_bad_seq?: number;
}

function summary(e: AuditEvent): string {
  const p = e.payload;
  if (e.action === "routed") {
    const rules = (p.rules_fired as string[] | undefined) ?? [];
    return `tier ${String(p.tier)} · conf ${(Number(p.confidence) * 100).toFixed(1)}% · exp. cost ${Number(p.expected_cost).toFixed(2)}${rules.length ? ` · rules ${rules.join(", ")}` : ""}`;
  }
  if (e.action === "executed") return `executed ${String(p.final_decision)}`;
  const reason = p.reason ? ` · “${String(p.reason)}”` : "";
  return `${String(p.ai_decision)} → ${String(p.final_decision)}${reason}`;
}

export function Audit() {
  const [params, setParams] = useSearchParams();
  const { version } = useLive();
  const caseId = params.get("case_id") ?? "";
  const query: Record<string, string> = { limit: "100" };
  if (caseId) query.case_id = caseId;
  const first = useApi<AuditEvent[]>(api.audit(query), 10000, version);
  const [older, setOlder] = useState<AuditEvent[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [filter, setFilter] = useState(caseId);

  useEffect(() => setOlder([]), [caseId]);

  const events = [...(first.data ?? []), ...older];
  const last = events[events.length - 1];

  const more = async () => {
    if (!last) return;
    setLoadingMore(true);
    try {
      const next = await getJson<AuditEvent[]>(api.audit({ ...query, before: String(last.seq) }));
      setOlder((o) => [...o, ...next]);
    } finally {
      setLoadingMore(false);
    }
  };

  const runVerify = async () => {
    setVerifying(true);
    try {
      setVerify(await getJson<Verify>(api.verify));
    } finally {
      setVerifying(false);
    }
  };

  return (
    <>
      <PageHead title="Audit log">
        Every routing decision, autonomous execution and reviewer decision, newest first. Each event stores the hash of the previous one, so any edit or deletion is
        detectable.
      </PageHead>
      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr)" }}>
        <section className="panel" aria-labelledby="chain-title">
          <div className="panel-head">
            <h2 id="chain-title">Chain integrity</h2>
            <button className="btn" type="button" onClick={runVerify} disabled={verifying}>
              {verifying ? "Verifying…" : "Verify chain"}
            </button>
          </div>
          <div className="panel-body" aria-live="polite">
            {verify === null ? (
              <p className="muted" style={{ margin: 0 }}>
                Recomputes every event hash from the first event and compares it with the stored chain.
              </p>
            ) : verify.valid ? (
              <p style={{ margin: 0 }}>
                <span className="pill good">Intact</span> {verify.events.toLocaleString()} events verified. Head <code>{verify.head?.slice(0, 24)}…</code>
              </p>
            ) : (
              <p role="alert" style={{ margin: 0 }}>
                <span className="pill bad">Broken</span> The chain fails at event #{verify.first_bad_seq} after {verify.events} valid events.
              </p>
            )}
          </div>
        </section>
        <section className="panel" aria-labelledby="events-title">
          <div className="panel-head">
            <h2 id="events-title">Events</h2>
            <form
              className="toolbar"
              style={{ margin: 0 }}
              onSubmit={(e) => {
                e.preventDefault();
                const next = new URLSearchParams(params);
                if (filter.trim()) next.set("case_id", filter.trim());
                else next.delete("case_id");
                setParams(next);
              }}
            >
              <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                Case id
                <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="e.g. payments-0-00012" maxLength={120} />
              </label>
              <button className="btn" type="submit">
                Filter
              </button>
              {caseId && (
                <button
                  className="btn ghost"
                  type="button"
                  onClick={() => {
                    setFilter("");
                    setParams(new URLSearchParams());
                  }}
                >
                  Clear
                </button>
              )}
            </form>
          </div>
          {first.loading && !first.data ? (
            <div className="panel-body">
              <Loading rows={8} label="Loading audit log" />
            </div>
          ) : first.error && !first.data ? (
            <div className="panel-body">
              <ErrorPanel error={first.error} retry={first.retry} what="the audit log" />
            </div>
          ) : events.length === 0 ? (
            <Empty title="No events">{caseId ? `No audit events for ${caseId}.` : "The log is empty."}</Empty>
          ) : (
            <>
              <div className="table-wrap" tabIndex={0} style={{ maxHeight: "65vh" }}>
                <table>
                  <caption className="skip-link">Audit events, newest first</caption>
                  <thead>
                    <tr>
                      <th scope="col" className="r">
                        #
                      </th>
                      <th scope="col">Time (UTC)</th>
                      <th scope="col">Case</th>
                      <th scope="col">Actor</th>
                      <th scope="col">Action</th>
                      <th scope="col">Detail</th>
                      <th scope="col">Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((e) => (
                      <tr key={e.seq}>
                        <td className="r">{e.seq}</td>
                        <td className="mono" style={{ whiteSpace: "nowrap" }}>
                          {e.ts.replace("T", " ").slice(0, 19)}
                        </td>
                        <td className="mono" style={{ whiteSpace: "nowrap" }}>
                          <Link to={`/queue/${encodeURIComponent(e.case_id)}`}>{e.case_id}</Link>
                        </td>
                        <td style={{ whiteSpace: "nowrap" }}>{e.actor}</td>
                        <td>{e.action}</td>
                        <td>{summary(e)}</td>
                        <td className="mono" title={`prev ${e.prev_hash}`}>
                          {e.hash.slice(0, 12)}…
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="panel-note" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                <span>{events.length} events shown</span>
                {last && last.seq > 1 && (
                  <button className="btn" type="button" onClick={more} disabled={loadingMore}>
                    {loadingMore ? "Loading…" : "Load older events"}
                  </button>
                )}
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}
