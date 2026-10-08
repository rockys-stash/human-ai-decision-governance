import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api, useApi, type Stats } from "../lib/api";
import { since } from "../lib/format";
import { useLive } from "../lib/live";
import { useReviewer } from "../lib/reviewer";

const NAV = [
  { to: "/queue", label: "Queue" },
  { to: "/audit", label: "Audit" },
  { to: "/policy", label: "Policy" },
  { to: "/experiments", label: "Experiments" },
  { to: "/calibration", label: "Calibration" },
  { to: "/method", label: "Method" },
];

type Theme = "system" | "light" | "dark";

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("decision-console-theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("decision-console-theme", theme);
    } catch {
      /* storage unavailable: preference lasts for this page view */
    }
  }, [theme]);
  const next: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
  return (
    <button className="btn ghost" type="button" onClick={() => setTheme(next[theme])} aria-label={`Theme: ${theme}. Switch to ${next[theme]}`}>
      Theme: {theme}
    </button>
  );
}

function pendingCount(stats: Stats | undefined, tier: "review" | "approval"): number | null {
  if (!stats) return null;
  return Object.values(stats.counts).reduce((n, c) => n + (c[`pending:${tier}`] ?? 0), 0);
}

function Counters() {
  const { version } = useLive();
  const stats = useApi<Stats>(api.stats, 5000, version);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 15000);
    return () => window.clearInterval(t);
  }, []);
  const review = pendingCount(stats.data, "review");
  const approval = pendingCount(stats.data, "approval");
  return (
    <div className="counters" aria-label="Queue status">
      <div className="counter">
        <span className="label">
          <span className="tier approval">
            <span className="shape" aria-hidden="true">
              ■
            </span>
          </span>
          Approvals waiting
        </span>
        <span className="value">{approval ?? "–"}</span>
      </div>
      <div className="counter">
        <span className="label">
          <span className="tier review">
            <span className="shape" aria-hidden="true">
              ▲
            </span>
          </span>
          Reviews waiting
        </span>
        <span className="value">{review ?? "–"}</span>
      </div>
      <div className="counter optional">
        <span className="label">Oldest wait</span>
        <span className="value">{stats.data?.oldest_pending_at ? since(stats.data.oldest_pending_at, now) : "–"}</span>
      </div>
    </div>
  );
}

function ReviewerStatus() {
  const { reviewer, signOut } = useReviewer();
  if (!reviewer) {
    return (
      <span className="pill" title="Decisions need a reviewer token">
        Read-only
      </span>
    );
  }
  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
      <span className="pill good">Signed in as {reviewer.replace("reviewer:", "")}</span>
      <button type="button" className="btn ghost" onClick={signOut}>
        Sign out
      </button>
    </span>
  );
}

export function Layout() {
  const location = useLocation();
  useEffect(() => {
    // Move focus to the page on navigation so screen-reader and keyboard users land on content.
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-row">
            <NavLink to="/queue" className="brand" aria-label="Decision Console, review queue">
              <span className="brand-mark" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 16 16">
                  <path d="M2 8h3l1.8-4 2.4 8L11 8h3" fill="none" strokeWidth="1.7" strokeLinejoin="round" strokeLinecap="round" />
                </svg>
              </span>
              <span>
                <span className="brand-name">Decision Console</span>
                <br />
                <span className="brand-sub">risk-adaptive human oversight</span>
              </span>
            </NavLink>
            <Counters />
            <ReviewerStatus />
            <ThemeToggle />
          </div>
          <nav className="tabs" aria-label="Sections">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? "active" : "")}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" className="main" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
