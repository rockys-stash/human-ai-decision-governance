import type { ReactNode } from "react";
import type { ApiError, Provenance, Tier } from "../lib/api";
import { TIER_LABEL } from "../lib/format";

const SHAPE: Record<Tier, string> = { autonomous: "●", review: "▲", approval: "■" };

/** Risk tier: always a shape and a word, never color alone. */
export function TierBadge({ tier }: { tier: Tier }) {
  return (
    <span className={`tier ${tier}`}>
      <span className="shape" aria-hidden="true">
        {SHAPE[tier]}
      </span>
      {TIER_LABEL[tier]}
    </span>
  );
}

export function Skeleton({ height = 16, width = "100%" }: { height?: number; width?: number | string }) {
  return <div className="skeleton" style={{ height, width }} aria-hidden="true" />;
}

export function Loading({ rows = 5, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div className="panel" role="status" aria-live="polite">
      <span className="skip-link">{label}…</span>
      <div className="panel-body" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Skeleton height={20} width="40%" />
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} height={28} />
        ))}
      </div>
    </div>
  );
}

export function ErrorPanel({ error, retry, what }: { error: ApiError; retry: () => void; what: string }) {
  return (
    <div className="state error" role="alert">
      <h2>Could not load {what}</h2>
      <p className="secondary">
        {error.status ? `HTTP ${error.status}: ` : ""}
        {error.message}
      </p>
      <p className="muted mono">{error.url}</p>
      <button className="btn" type="button" onClick={retry}>
        Retry
      </button>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="state">
      <h2>{title}</h2>
      {children && <div className="secondary">{children}</div>}
    </div>
  );
}

export function Pending({ what }: { what: string }) {
  return (
    <div className="panel">
      <Empty title="Status: pending">
        No completed run of <code>{what}</code> was found. Run <code>uv run governance run configs/{what}.yaml</code>.
      </Empty>
    </div>
  );
}

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { id: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" aria-pressed={o.id === value} onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function ProvenanceLine({ p }: { p: Provenance }) {
  return (
    <p className="muted" style={{ fontSize: 12.5, margin: 0 }}>
      Source <code>results/{p.experiment}/{p.run_id}</code> · commit <code>{p.commit.slice(0, 7)}</code> · {p.seeds} seeds · model{" "}
      {p.model}+{p.calibrator}
    </p>
  );
}

export function PageHead({ title, children, actions }: { title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {actions}
    </div>
  );
}
