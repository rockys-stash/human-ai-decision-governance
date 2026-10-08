import { useCallback, useEffect, useRef, useState } from "react";

/* ---------- types mirrored from the API ---------- */
export type Tier = "autonomous" | "review" | "approval";
export type Domain = "payments" | "credit" | "eligibility";
export type Regime = "human_only" | "ai_only" | "blanket_approval" | "risk_adaptive";

export interface Agg {
  mean: number | null;
  std: number | null;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
}

export interface Meta {
  domains: { id: Domain; label: string }[];
  tiers: Tier[];
  regimes: { id: Regime; label: string }[];
  routers: Record<string, string>;
  writes_enabled: boolean;
}

export interface CaseSummary {
  id: string;
  domain: Domain;
  seq: number;
  tier: Tier;
  status: "pending" | "decided" | "auto_executed";
  ai_decision: string;
  confidence: number;
  stake: number;
  expected_cost: number;
  rules_fired: string[];
  final_decision: string | null;
  decided_by: string | null;
  decided_at: string | null;
  created_at: string;
  truth?: string;
  correct?: boolean;
}

export interface AuditEvent {
  seq: number;
  ts: string;
  case_id: string;
  actor: string;
  action: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
}

export interface Routing {
  policy_id: string;
  policy_version: string;
  policy_hash: string;
  model: string;
  p_raw: number;
  p: number;
  ai_decision: string;
  confidence: number;
  stake: number;
  expected_cost: number;
  thresholds: { review: number; approval: number };
  cost_tier: Tier;
  rules_fired: string[];
  tier: Tier;
  positive_action: string;
  negative_action: string;
  stake_unit: string;
  decision_threshold: number;
  cost_false_approve: number;
  cost_false_decline: number;
  policy_rules: Record<string, string>;
}

export interface CaseDetail extends CaseSummary {
  routing: Routing;
  features: Record<string, string | number>;
  explanation: { feature: string; value: string | number; reference: string | number; effect: number }[];
  reason: string | null;
  audit: AuditEvent[];
}

export interface Stats {
  counts: Record<string, Record<string, number>>;
  oldest_pending_at: string | null;
  human_decisions: number;
  override_rate: number | null;
  override_precision: number | null;
  accepted_wrong_ai: number;
  caught_wrong_ai: number;
  human_accuracy: number | null;
}

export interface Condition {
  field: string;
  op: string;
  value: unknown;
}

export interface PolicyDoc {
  id: string;
  version: string;
  domain: Domain;
  description: string;
  thresholds: { review: number; approval: number };
  rules: { id: string; description: string; route: Tier; when: Condition[] }[];
  hash: string;
  path: string;
}

export interface Provenance {
  experiment: string;
  description: string;
  kind: string;
  run_id: string;
  created_at: string;
  commit: string;
  base_seed: number;
  seeds: number;
  domains: Domain[];
  model: string;
  calibrator: string;
  reviewer: Record<string, number>;
  staffing: Record<string, number>;
  runtime_seconds: number;
}

export interface ExperimentInfo extends Partial<Provenance> {
  experiment: string;
  status: "pending" | "complete";
}

export interface Pair {
  metric: string;
  a: string;
  b: string;
  diff: number | null;
  ci_low: number | null;
  ci_high: number | null;
  p_value: number;
  p_holm?: number;
}

export interface RegimeStats {
  [metric: string]: unknown;
  accuracy: Agg;
  loss_per_1000: Agg;
  share_human: Agg;
  reviewer_hours_per_1000: Agg;
  decision_minutes_median: Agg;
  decision_minutes_p95: Agg;
  override_rate: Agg;
  override_precision: Agg;
  automation_bias_rate: Agg;
  appropriate_reliance: Agg;
  high_stake_errors_per_1000: Agg;
  errors: Record<string, Agg>;
  tier_share?: Record<Tier, Agg>;
  error_by_tier?: Record<Tier, Agg>;
  rules_fired_share?: Record<string, number>;
}

export interface E2Summary {
  domains: Record<Domain, { regimes: Record<Regime, RegimeStats>; pairwise: Pair[] }>;
  policies: Record<Domain, PolicyDoc>;
  provenance: Provenance;
}

export interface CurvePoint {
  target_share: number;
  loss_per_1000: Agg;
  accuracy: Agg;
  share_human: Agg;
  reviewer_hours_per_1000: Agg;
}

export interface E3Summary {
  domains: Record<
    Domain,
    {
      curves: Record<string, CurvePoint[]>;
      policy: Omit<CurvePoint, "target_share">;
      matched: Pair[];
    }
  >;
  matched_share: number;
  mode: string;
  provenance: Provenance;
}

export interface E1Summary {
  by_condition: Record<string, Record<string, Agg>>;
  reliability: Record<string, { conf: number; acc: number; count: number; lo: number; hi: number }[]>;
  pairwise: (Pair & { domain: Domain; model: string })[];
  provenance: Provenance;
}

export interface SensitivityRow {
  value: number;
  lowest_loss_regime: Regime;
  [key: string]: unknown;
}

export interface E4Summary {
  axes: Record<string, Record<Domain, SensitivityRow[]>>;
  provenance: Provenance;
}

export interface ShiftRow {
  level: number;
  ece: Agg;
  brier: Agg;
  ai_accuracy: Agg;
  mean_confidence: Agg;
  autonomous_share: Agg;
  [regime: string]: unknown;
}

export interface E5Summary {
  shifts: Record<"covariate" | "concept", ShiftRow[]>;
  provenance: Provenance;
}

/* ---------- fetching ---------- */
export class ApiError extends Error {
  constructor(
    public url: string,
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const cache = new Map<string, unknown>();
const CACHEABLE = /^\/api\/(experiments|policies|meta)/;

async function errorFrom(url: string, res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") detail = body.detail;
    else if (Array.isArray(body.detail)) {
      detail = body.detail.map((d: { msg?: string }) => d.msg ?? "invalid input").join("; ");
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(url, res.status, detail);
}

export async function getJson<T>(url: string, headers: Record<string, string> = {}): Promise<T> {
  if (cache.has(url)) return cache.get(url) as T;
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json", ...headers } });
  } catch {
    throw new ApiError(url, 0, "The console API could not be reached.");
  }
  if (!res.ok) throw await errorFrom(url, res);
  const data = (await res.json()) as T;
  if (CACHEABLE.test(url)) cache.set(url, data);
  return data;
}

export async function postJson<T>(url: string, body: unknown, headers: Record<string, string>): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", ...headers },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(url, 0, "The console API could not be reached.");
  }
  if (!res.ok) throw await errorFrom(url, res);
  return (await res.json()) as T;
}

export interface ApiState<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  retry: () => void;
}

/** Fetches JSON and keeps the previous data while a new URL loads. ``refreshMs`` polls. */
export function useApi<T>(url: string | null, refreshMs?: number, version = 0): ApiState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(url !== null);
  const [nonce, setNonce] = useState(0);
  const current = useRef(url);

  useEffect(() => {
    current.current = url;
    if (url === null) {
      setLoading(false);
      return;
    }
    let alive = true;
    const load = (initial: boolean) => {
      if (initial) {
        setLoading(true);
        setError(undefined);
      }
      getJson<T>(url)
        .then((d) => {
          if (alive && current.current === url) {
            setData(d);
            setError(undefined);
          }
        })
        .catch((e: unknown) => {
          if (alive && current.current === url) setError(e instanceof ApiError ? e : new ApiError(url, 0, String(e)));
        })
        .finally(() => {
          if (alive && current.current === url && initial) setLoading(false);
        });
    };
    load(true);
    const timer = refreshMs ? window.setInterval(() => load(false), refreshMs) : undefined;
    return () => {
      alive = false;
      if (timer) window.clearInterval(timer);
    };
  }, [url, nonce, refreshMs, version]);

  const retry = useCallback(() => {
    if (url) cache.delete(url);
    setNonce((n) => n + 1);
  }, [url]);

  return { data, error, loading, retry };
}

export const api = {
  meta: "/api/meta",
  stats: "/api/stats",
  experiments: "/api/experiments",
  experiment: (exp: string) => `/api/experiments/${encodeURIComponent(exp)}`,
  policies: "/api/policies",
  queue: (params: Record<string, string>) => `/api/queue?${new URLSearchParams(params).toString()}`,
  case: (id: string) => `/api/cases/${encodeURIComponent(id)}`,
  decide: (id: string) => `/api/cases/${encodeURIComponent(id)}/decision`,
  audit: (params: Record<string, string>) => `/api/audit?${new URLSearchParams(params).toString()}`,
  verify: "/api/audit/verify",
  reviewer: "/api/reviewer",
};
