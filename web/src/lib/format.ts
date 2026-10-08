import type { Agg, Domain, Regime, Tier } from "./api";

export const DOMAINS: Domain[] = ["payments", "credit", "eligibility"];
export const DOMAIN_LABEL: Record<Domain, string> = {
  payments: "Payments",
  credit: "Credit",
  eligibility: "Eligibility",
};
export const DOMAIN_SOURCE: Record<Domain, string> = {
  payments: "synthetic, known true probability",
  credit: "UCI German Credit",
  eligibility: "UCI Adult",
};

export const REGIMES: Regime[] = ["human_only", "ai_only", "blanket_approval", "risk_adaptive"];
export const REGIME_LABEL: Record<Regime, string> = {
  human_only: "Human only",
  ai_only: "AI only",
  blanket_approval: "AI + blanket approval",
  risk_adaptive: "Risk-adaptive",
};
/** Fixed series order (docs/DESIGN.md): never re-assigned when a regime is hidden. */
export const REGIME_COLOR: Record<Regime, string> = {
  human_only: "var(--s1)",
  ai_only: "var(--s2)",
  blanket_approval: "var(--s3)",
  risk_adaptive: "var(--s4)",
};

export const ROUTERS = ["expected_cost", "expected_cost_uncalibrated", "confidence_only", "stake_only", "random"] as const;
export const ROUTER_LABEL: Record<string, string> = {
  expected_cost: "Expected cost (calibrated)",
  expected_cost_uncalibrated: "Expected cost (uncalibrated)",
  confidence_only: "Confidence only",
  stake_only: "Stake only",
  random: "Random audit",
};
export const ROUTER_COLOR: Record<string, string> = {
  expected_cost: "var(--s1)",
  expected_cost_uncalibrated: "var(--s2)",
  confidence_only: "var(--s3)",
  stake_only: "var(--s4)",
  random: "var(--ref)",
};

export const TIER_LABEL: Record<Tier, string> = {
  autonomous: "Autonomous",
  review: "Review",
  approval: "Approval",
};

export function pct(v: number | null | undefined, digits = 1): string {
  return v === null || v === undefined ? "n/a" : `${(v * 100).toFixed(digits)}%`;
}

export function num(v: number | null | undefined, digits = 0): string {
  if (v === null || v === undefined) return "n/a";
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** Compact magnitude for large losses (1,234,567 -> 1.23M). */
export function compact(v: number | null | undefined): string {
  if (v === null || v === undefined) return "n/a";
  const a = Math.abs(v);
  if (a >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (a >= 1e4) return `${(v / 1e3).toFixed(1)}k`;
  return num(v, a < 10 ? 2 : 0);
}

export function aggText(s: Agg | undefined, f: (v: number) => string): string {
  if (!s || s.mean === null) return "n/a";
  if (s.ci_low === null || s.ci_high === null) return f(s.mean);
  return `${f(s.mean)} [${f(s.ci_low)}, ${f(s.ci_high)}]`;
}

export function money(v: number, unit: string): string {
  if (unit === "cost units") return num(v, 2);
  return `${num(v, v < 100 ? 2 : 0)} ${unit === "currency units" ? "" : unit}`.trim();
}

export function since(iso: string | null | undefined, now = Date.now()): string {
  if (!iso) return "n/a";
  const s = Math.max(0, (now - Date.parse(iso)) / 1000);
  if (s < 60) return `${Math.round(s)}s`;
  if (s < 3600) return `${Math.round(s / 60)}m`;
  if (s < 86400) return `${(s / 3600).toFixed(1)}h`;
  return `${(s / 86400).toFixed(1)}d`;
}

export function humanFeature(k: string): string {
  return k.replace(/_/g, " ");
}
