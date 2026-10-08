import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ErrorPanel, Empty, Loading, Segmented, TierBadge } from "../components/ui";
import { api, ApiError, postJson, useApi, type CaseDetail, type CaseSummary, type Stats } from "../lib/api";
import { DOMAIN_LABEL, DOMAINS, humanFeature, money, num, pct, since } from "../lib/format";
import { useLive } from "../lib/live";
import { useReviewer } from "../lib/reviewer";

type View = "pending" | "decided" | "auto_executed";

const VIEW_LABEL: Record<View, string> = { pending: "Waiting", decided: "Decided", auto_executed: "Autonomous" };

function thr(v: number): string {
  return num(v, v < 10 ? 2 : 0);
}

function isTyping(el: Element | null): boolean {
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || (el as HTMLElement).isContentEditable);
}

export function Queue() {
  const { caseId } = useParams();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { version } = useLive();
  const domain = params.get("domain") ?? "";
  const tier = params.get("tier") ?? "";
  const view = (params.get("view") as View | null) ?? "pending";
  const query: Record<string, string> = { status: view, limit: "200" };
  if (domain) query.domain = domain;
  if (tier) query.tier = tier;
  const list = useApi<CaseSummary[]>(api.queue(query), 10000, version);
  const stats = useApi<Stats>(api.stats, undefined, version);
  const items = useMemo(() => list.data ?? [], [list.data]);
  const [announce, setAnnounce] = useState("");
  const lastCount = useRef<number | null>(null);

  useEffect(() => {
    if (view !== "pending" || !list.data) return;
    if (lastCount.current !== null && list.data.length > lastCount.current) {
      setAnnounce(`${list.data.length - lastCount.current} new cases in the queue`);
    }
    lastCount.current = list.data.length;
  }, [list.data, view]);

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };
  const qs = params.toString() ? `?${params.toString()}` : "";
  const open = useCallback((id: string) => navigate(`/queue/${encodeURIComponent(id)}${qs}`), [navigate, qs]);

  const index = items.findIndex((c) => c.id === caseId);
  const move = useCallback(
    (delta: number) => {
      if (!items.length) return;
      const next = index < 0 ? (delta > 0 ? 0 : items.length - 1) : Math.min(items.length - 1, Math.max(0, index + delta));
      const target = items[next];
      if (target) open(target.id);
    },
    [items, index, open],
  );

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(document.activeElement)) return;
      if (e.key === "j") move(1);
      else if (e.key === "k") move(-1);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [move]);

  // Keep the selected row in view when moving with j/k.
  useEffect(() => {
    if (caseId) document.getElementById(`row-${caseId}`)?.scrollIntoView({ block: "nearest" });
  }, [caseId]);

  const autoCount = stats.data ? Object.values(stats.data.counts).reduce((n, c) => n + (c["auto_executed:autonomous"] ?? 0), 0) : null;

  return (
    <>
      <div className="skip-link" aria-live="polite" role="status">
        {announce}
      </div>
      <div className={`queue${caseId ? " has-selection" : ""}`}>
        <section className="panel queue-list" aria-labelledby="queue-title">
          <div className="panel-head" style={{ flexDirection: "column", alignItems: "stretch" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
              <h1 id="queue-title">Review queue</h1>
              <span className="muted num">{list.data ? `${items.length} ${VIEW_LABEL[view].toLowerCase()}` : ""}</span>
            </div>
            <Segmented
              label="Queue view"
              options={(["pending", "decided", "auto_executed"] as View[]).map((v) => ({ id: v, label: VIEW_LABEL[v] }))}
              value={view}
              onChange={(v) => setParam("view", v === "pending" ? "" : v)}
            />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <label className="field" style={{ flex: 1, minWidth: 130 }}>
                Domain
                <select value={domain} onChange={(e) => setParam("domain", e.target.value)}>
                  <option value="">All domains</option>
                  {DOMAINS.map((d) => (
                    <option key={d} value={d}>
                      {DOMAIN_LABEL[d]}
                    </option>
                  ))}
                </select>
              </label>
              {view !== "auto_executed" && (
                <label className="field" style={{ flex: 1, minWidth: 130 }}>
                  Tier
                  <select value={tier} onChange={(e) => setParam("tier", e.target.value)}>
                    <option value="">Review and approval</option>
                    <option value="approval">Approval only</option>
                    <option value="review">Review only</option>
                  </select>
                </label>
              )}
            </div>
            <div className="shortcuts" aria-label="Keyboard shortcuts">
              <span>
                <span className="kbd">j</span>/<span className="kbd">k</span> next/previous
              </span>
              <span>
                <span className="kbd">a</span> accept or approve
              </span>
              <span>
                <span className="kbd">o</span> override
              </span>
            </div>
          </div>
          {list.loading && !list.data ? (
            <div className="panel-body">
              <Loading rows={6} label="Loading queue" />
            </div>
          ) : list.error && !list.data ? (
            <div className="panel-body">
              <ErrorPanel error={list.error} retry={list.retry} what="the queue" />
            </div>
          ) : items.length === 0 ? (
            <Empty title={view === "pending" ? "No cases waiting" : "Nothing here yet"}>
              {view === "pending" && autoCount !== null ? `${num(autoCount)} cases were decided autonomously under the active policies.` : null}
            </Empty>
          ) : (
            <ul className={`queue-items${list.loading ? " stale" : ""}`} aria-label="Cases">
              {items.map((c) => (
                <li key={c.id}>
                  <Link
                    id={`row-${c.id}`}
                    to={`/queue/${encodeURIComponent(c.id)}${qs}`}
                    className="queue-item"
                    aria-current={c.id === caseId ? "true" : undefined}
                  >
                    <span>
                      <span className="id">{c.id}</span>
                      <br />
                      <span className="rec">
                        AI recommends <strong>{c.ai_decision}</strong>
                      </span>
                    </span>
                    <TierBadge tier={c.tier} />
                    <span className="meta">
                      <span>conf {pct(c.confidence, 0)}</span>
                      <span>exp. cost {num(c.expected_cost, c.expected_cost < 10 ? 2 : 0)}</span>
                      {c.rules_fired.length > 0 && <span>{c.rules_fired.length} rule{c.rules_fired.length > 1 ? "s" : ""}</span>}
                      {c.status === "decided" && c.correct !== undefined && (
                        <span className={c.correct ? "pill good" : "pill bad"}>{c.correct ? "correct" : "wrong"}</span>
                      )}
                      {c.status === "pending" && <span>waiting {since(c.created_at)}</span>}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="inspector" aria-label="Case inspector">
          {caseId ? (
            <CaseInspector key={caseId} caseId={caseId} backTo={`/queue${qs}`} onDecided={(msg) => setAnnounce(msg)} onNext={() => move(1)} />
          ) : (
            <div className="panel">
              <Empty title="Select a case">Open the first case with j, or choose one from the list. Approvals are listed first, then reviews by expected cost.</Empty>
            </div>
          )}
        </section>
      </div>
    </>
  );
}

function CaseInspector({ caseId, backTo, onDecided, onNext }: { caseId: string; backTo: string; onDecided: (msg: string) => void; onNext: () => void }) {
  const { version, bump } = useLive();
  const detail = useApi<CaseDetail>(api.case(caseId), undefined, version);
  const c = detail.data;
  if (detail.loading && !c) return <Loading rows={8} label="Loading case" />;
  if (detail.error && !c) return <ErrorPanel error={detail.error} retry={detail.retry} what="this case" />;
  if (!c) return null;
  const r = c.routing;
  const unit = r.stake_unit;
  const maxEffect = Math.max(0.01, ...c.explanation.map((e) => Math.abs(e.effect)));
  return (
    <>
      <Link className="back-link btn ghost" to={backTo} style={{ width: "max-content" }}>
        Back to queue
      </Link>
      <article className="panel" aria-labelledby="case-title">
        <div className="panel-head">
          <div>
            <h2 id="case-title" className="mono" style={{ fontSize: 15 }}>
              {c.id}
            </h2>
            <span className="muted">
              {DOMAIN_LABEL[c.domain]} · arrival #{c.seq + 1} · policy <code>{r.policy_id}</code> v{r.policy_version} <code>{r.policy_hash}</code>
            </span>
          </div>
          <TierBadge tier={c.tier} />
        </div>
        <div className="panel-body">
          <div className="recommendation">
            <div className="stat">
              <span className="label">AI recommendation</span>
              <span className="big">{c.ai_decision}</span>
            </div>
            <div className="stat">
              <span className="label">P({r.positive_action} is correct)</span>
              <span className="value">{pct(r.p)}</span>
            </div>
            <div className="stat">
              <span className="label">Confidence in recommendation</span>
              <span className="value">{pct(c.confidence)}</span>
            </div>
            <div className="stat">
              <span className="label">Stake</span>
              <span className="value">{money(c.stake, unit)}</span>
            </div>
            <div className="stat">
              <span className="label">Expected cost if executed</span>
              <span className="value">{num(c.expected_cost, c.expected_cost < 10 ? 2 : 0)}</span>
            </div>
          </div>
        </div>
        <div className="panel-note" style={{ borderTop: "1px solid var(--rule)" }}>
          The agent recommends {r.positive_action} only when P({r.positive_action} is correct) ≥ {pct(r.decision_threshold, 1)}, because a wrong{" "}
          {r.positive_action} costs {num(r.cost_false_approve, 2)} × stake and a wrong {r.negative_action} {num(r.cost_false_decline, 2)} × stake. Confidence is the
          calibrated probability that the recommendation is correct, so it can be below 50% when the cheaper mistake is chosen. Expected cost = (1 − confidence) × cost if
          wrong.
        </div>
      </article>

      <DecisionBox c={c} onDecided={(msg) => { onDecided(msg); bump(); }} onNext={onNext} />

      <div className="grid two">
        <section className="panel" aria-labelledby="why-title">
          <div className="panel-head">
            <h3 id="why-title">{r.tier === "autonomous" ? "Why this case ran autonomously" : "Why a person sees this case"}</h3>
          </div>
          <div className="panel-body">
            <ul className="why">
              <li>
                Expected cost {num(r.expected_cost, r.expected_cost < 10 ? 2 : 0)} against thresholds review ≥ {thr(r.thresholds.review)} and approval ≥{" "}
                {thr(r.thresholds.approval)}: cost tier <TierBadge tier={r.cost_tier} />.
              </li>
              {r.rules_fired.map((id) => (
                <li key={id}>
                  Rule <code>{id}</code>: {r.policy_rules[id] ?? "policy rule"}.
                </li>
              ))}
              {r.rules_fired.length === 0 && <li>No hard rule fired; the tier comes from expected cost alone.</li>}
              <li>
                Final tier <TierBadge tier={r.tier} />
                {r.tier === "approval"
                  ? ": the decision cannot execute without a named approver and a justification."
                  : r.tier === "review"
                    ? ": a reviewer confirms or overrides the AI."
                    : ": the AI decision executed without a person, and the route is logged."}
              </li>
            </ul>
          </div>
        </section>
        <section className="panel" aria-labelledby="ev-title">
          <div className="panel-head">
            <h3 id="ev-title">Evidence behind the recommendation</h3>
          </div>
          <div className="panel-body">
            {c.explanation.length === 0 ? (
              <p className="muted">No feature differs from its training reference.</p>
            ) : (
              c.explanation.map((e) => {
                const w = (Math.abs(e.effect) / maxEffect) * 50;
                return (
                  <div className="evidence-row" key={e.feature}>
                    <span>
                      <strong style={{ fontWeight: 500 }}>{humanFeature(e.feature)}</strong>
                      <br />
                      <span className="muted" style={{ fontSize: 12.5 }}>
                        {String(e.value)} (typical {String(e.reference)})
                      </span>
                    </span>
                    <span className="evidence-bar" aria-hidden="true">
                      <span className="axis" />
                      <span className={`bar ${e.effect >= 0 ? "up" : "down"}`} style={e.effect >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }} />
                    </span>
                    <span className="num" style={{ textAlign: "right" }}>
                      {e.effect >= 0 ? "+" : "−"}
                      {Math.abs(e.effect * 100).toFixed(1)} pp
                    </span>
                  </div>
                );
              })
            )}
          </div>
          <div className="panel-note">
            Change in the model's score for “{r.positive_action}” when the feature is replaced by its typical training value. Blue pushes toward {r.positive_action}, orange
            toward {r.negative_action}.
          </div>
        </section>
      </div>

      <section className="panel" aria-labelledby="feat-title">
        <div className="panel-head">
          <h3 id="feat-title">Case record</h3>
        </div>
        <div className="panel-body">
          <dl className="kv">
            {Object.entries(c.features).map(([k, v]) => (
              <div key={k} style={{ display: "contents" }}>
                <dt>{humanFeature(k)}</dt>
                <dd>{String(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="panel" aria-labelledby="trail-title">
        <div className="panel-head">
          <h3 id="trail-title">Audit trail</h3>
          <Link to={`/audit?case_id=${encodeURIComponent(c.id)}`}>Open in audit log</Link>
        </div>
        <div className="table-wrap" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">Time (UTC)</th>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Event hash</th>
              </tr>
            </thead>
            <tbody>
              {[...c.audit].reverse().map((e) => (
                <tr key={e.seq}>
                  <td className="mono">{e.ts.replace("T", " ").slice(0, 19)}</td>
                  <td>{e.actor}</td>
                  <td>{e.action}</td>
                  <td className="mono">{e.hash.slice(0, 16)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function SignIn() {
  const { signIn, checking, error } = useReviewer();
  const [token, setToken] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (token.trim()) void signIn(token.trim());
  };
  return (
    <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <p className="secondary" style={{ margin: 0 }}>
        You are viewing the queue read-only. Decisions are recorded under the reviewer named by your token, so sign in with the token from{" "}
        <code>GOVERNANCE_REVIEWER_TOKENS</code>.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label className="field" style={{ flex: 1, minWidth: 200 }}>
          Reviewer token
          <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />
        </label>
        <button className="btn" type="submit" disabled={checking || !token.trim()}>
          {checking ? "Checking…" : "Sign in"}
        </button>
      </div>
      {error && (
        <p role="alert" style={{ color: "var(--bad-ink)", margin: 0 }}>
          {error}
        </p>
      )}
    </form>
  );
}

function DecisionBox({ c, onDecided, onNext }: { c: CaseDetail; onDecided: (msg: string) => void; onNext: () => void }) {
  const { reviewer, headers } = useReviewer();
  const [mode, setMode] = useState<"confirm" | "override">("confirm");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const approval = c.tier === "approval";
  const pending = c.status === "pending";
  const r = c.routing;
  const other = c.ai_decision === r.positive_action ? r.negative_action : r.positive_action;
  const needsReason = mode === "override" || approval;

  const submit = useCallback(
    async (action: "accept" | "approve" | "override") => {
      setBusy(true);
      setErr(null);
      try {
        await postJson(api.decide(c.id), { action, reason: reason.trim() || null }, headers);
        onDecided(`Decision recorded for ${c.id}: ${action === "override" ? `overridden to ${other}` : `${c.ai_decision} confirmed`}.`);
      } catch (e) {
        setErr(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [c.id, c.ai_decision, reason, headers, onDecided, other],
  );

  useEffect(() => {
    if (!pending || !reviewer) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(document.activeElement)) return;
      if (e.key === "a") {
        e.preventDefault();
        setMode("confirm");
        if (approval) reasonRef.current?.focus();
        else void submit("accept");
      } else if (e.key === "o") {
        e.preventDefault();
        setMode("override");
        window.setTimeout(() => reasonRef.current?.focus(), 0);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pending, reviewer, approval, submit]);

  if (!pending) {
    return (
      <section className="outcome" aria-labelledby="outcome-title">
        <h3 id="outcome-title" style={{ marginBottom: 6 }}>
          {c.status === "auto_executed" ? "Executed autonomously" : `Decided by ${(c.decided_by ?? "").replace("reviewer:", "")}`}
        </h3>
        <dl className="kv">
          <dt>Final decision</dt>
          <dd style={{ textTransform: "capitalize" }}>
            {c.final_decision}
            {c.final_decision !== c.ai_decision && " (AI overridden)"}
          </dd>
          {c.reason && (
            <>
              <dt>Reason</dt>
              <dd>{c.reason}</dd>
            </>
          )}
          <dt>Simulated outcome</dt>
          <dd>
            Correct action was <strong>{c.truth}</strong>{" "}
            <span className={c.correct ? "pill good" : "pill bad"}>{c.correct ? "decision correct" : "decision wrong"}</span>
          </dd>
        </dl>
        <p className="muted" style={{ fontSize: 12.5, margin: "8px 0 0" }}>
          The outcome is the dataset label (or simulated payment outcome), revealed only after a decision exists.
        </p>
        {c.status === "decided" && (
          <button className="btn" type="button" style={{ marginTop: 8 }} onClick={onNext}>
            Next case (j)
          </button>
        )}
      </section>
    );
  }

  return (
    <section className="decision-box" aria-labelledby="decide-title">
      <div className="panel-head">
        <h3 id="decide-title">{approval ? "Mandatory approval" : "Review"}</h3>
        <span className="muted">{approval ? "A named approver and a justification are required." : "Confirm the AI, or override it with a reason."}</span>
      </div>
      <div className="panel-body">
        {!reviewer ? (
          <SignIn />
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submit(mode === "override" ? "override" : approval ? "approve" : "accept");
            }}
            style={{ display: "flex", flexDirection: "column", gap: 12 }}
          >
            <Segmented
              label="Decision"
              options={[
                { id: "confirm", label: approval ? `Approve: ${c.ai_decision}` : `Accept: ${c.ai_decision}` },
                { id: "override", label: `Override: ${other}` },
              ]}
              value={mode}
              onChange={setMode}
            />
            {needsReason && (
              <label className="field">
                {mode === "override" ? "Reason for overriding (required, 10+ characters)" : "Justification for approval (required, 10+ characters)"}
                <textarea ref={reasonRef} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
              </label>
            )}
            <div className="decision-actions">
              <button className="btn primary" type="submit" disabled={busy || (needsReason && reason.trim().length < 10)}>
                {busy ? "Recording…" : mode === "override" ? `Override to ${other}` : approval ? `Approve ${c.ai_decision}` : `Accept ${c.ai_decision}`}
              </button>
              <span className="muted" style={{ fontSize: 12.5 }}>
                Recorded as {reviewer.replace("reviewer:", "")} in the hash-chained audit log.
              </span>
            </div>
            {err && (
              <p role="alert" style={{ color: "var(--bad-ink)", margin: 0 }}>
                {err}
              </p>
            )}
          </form>
        )}
      </div>
    </section>
  );
}
