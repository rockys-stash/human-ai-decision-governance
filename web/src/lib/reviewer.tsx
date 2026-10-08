import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, getJson } from "./api";

const KEY = "decision-console-reviewer-token";

interface ReviewerState {
  token: string | null;
  reviewer: string | null;
  checking: boolean;
  error: string | null;
  signIn: (token: string) => Promise<boolean>;
  signOut: () => void;
  headers: Record<string, string>;
}

const Ctx = createContext<ReviewerState | null>(null);

function readToken(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/** Reviewer sign-in. The token lives in sessionStorage only (cleared when the tab closes) and is
 * sent as X-Reviewer-Token; the server derives the reviewer's identity from it. */
export function ReviewerProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken);
  const [reviewer, setReviewer] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async (t: string) => {
    setChecking(true);
    setError(null);
    try {
      const r = await getJson<{ reviewer: string }>(api.reviewer, { "X-Reviewer-Token": t });
      setReviewer(r.reviewer);
      setToken(t);
      try {
        sessionStorage.setItem(KEY, t);
      } catch {
        /* storage unavailable: sign-in lasts for this page view */
      }
      return true;
    } catch (e) {
      setReviewer(null);
      setToken(null);
      try {
        sessionStorage.removeItem(KEY);
      } catch {
        /* ignore */
      }
      setError(e instanceof ApiError && e.status === 403 ? "Reviewer decisions are disabled on this server." : "That reviewer token was not accepted.");
      return false;
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    const t = readToken();
    if (t) void check(t);
  }, [check]);

  const signOut = useCallback(() => {
    setToken(null);
    setReviewer(null);
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo<ReviewerState>(
    () => ({
      token,
      reviewer,
      checking,
      error,
      signIn: check,
      signOut,
      headers: token ? { "X-Reviewer-Token": token } : ({} as Record<string, string>),
    }),
    [token, reviewer, checking, error, check, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useReviewer(): ReviewerState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useReviewer outside ReviewerProvider");
  return v;
}
