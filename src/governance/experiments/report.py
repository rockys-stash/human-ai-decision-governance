"""Regenerates the report's tables (Markdown) and figures (SVG) from the latest completed runs.

Every number written here is read from a ``summary.json`` produced by ``governance run``; each
table states the run id and commit it came from. Experiments without a completed run are reported
as pending rather than omitted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance.regimes.regimes import REGIME_LABELS, REGIMES, ROUTERS

EXPERIMENTS = ("e1_calibration", "e2_regimes", "e3_frontier", "e4_sensitivity", "e5_shift")
DOMAIN_LABELS = {
    "credit": "Credit (German Credit)",
    "eligibility": "Eligibility (Adult)",
    "payments": "Payments (synthetic)",
}
ROUTER_LABELS = {
    "expected_cost": "Expected cost (calibrated)",
    "expected_cost_uncalibrated": "Expected cost (uncalibrated)",
    "confidence_only": "Confidence only",
    "stake_only": "Stake only",
    "random": "Random audit",
    "policy": "Configured policy",
}
CAL_LABELS = {"none": "none", "platt": "Platt", "isotonic": "isotonic"}

# Light-mode chart tokens from docs/DESIGN.md: regimes keep this order everywhere.
INK, INK2, MUTED, GRID, SURFACE = "#0e0f11", "#45474d", "#62656c", "#e2e3e6", "#ffffff"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
REFERENCE = "#8d9098"
REGIME_COLOR = dict(zip(REGIMES, SERIES, strict=True))
ROUTER_COLOR = {
    "expected_cost": SERIES[0],
    "expected_cost_uncalibrated": SERIES[1],
    "confidence_only": SERIES[2],
    "stake_only": SERIES[3],
    "random": REFERENCE,
}


# --- loading and formatting --------------------------------------------------------------------
def _latest(root: Path, exp: str) -> dict[str, Any] | None:
    marker = root / "results" / exp / "LATEST"
    if not marker.exists():
        return None
    run = root / "results" / exp / marker.read_text().strip() / "summary.json"
    if not run.exists():
        return None
    data: dict[str, Any] = json.loads(run.read_text())
    return data


def _num(v: float | None, digits: int = 1, pct: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v * (100 if pct else 1):.{digits}f}"


def _ci(s: dict[str, Any] | None, digits: int = 1, pct: bool = False) -> str:
    """``mean [low, high]`` from an aggregate() result."""
    if not s or s.get("mean") is None:
        return "n/a"
    k = 100 if pct else 1
    return (
        f"{s['mean'] * k:.{digits}f} [{s['ci_low'] * k:.{digits}f}, {s['ci_high'] * k:.{digits}f}]"
    )


def _p(v: float | None) -> str:
    if v is None:
        return "n/a"
    return "<0.001" if v < 0.001 else f"{v:.3f}"


def _prov(s: dict[str, Any]) -> str:
    p = s["provenance"]
    return (
        f"_Source: `results/{p['experiment']}/{p['run_id']}` · commit `{p['commit'][:12]}` · "
        f"{p['seeds']} seeds from base {p['base_seed']} · runtime {p['runtime_seconds']} s._"
    )


def _pending(title: str, exp: str) -> list[str]:
    return [f"## {title}", "", f"Status: pending (no completed run of `{exp}`).", ""]


# --- tables ------------------------------------------------------------------------------------
def _e1_tables(s: dict[str, Any]) -> list[str]:
    out = ["## E1: Calibration of decision confidence", "", _prov(s), "",
           "Confidence is the estimated probability that the decision taken is correct. Values are means over seeds "
           "with 95% bootstrap CIs; ECE uses 15 equal-mass bins on the test stream.", "",
           "| Domain | Model | Calibrator | Accuracy (%) | Mean confidence (%) | ECE (pp) | MCE (pp) | Brier | NLL |",
           "|---|---|---|---|---|---|---|---|---|"]  # fmt: skip
    for key, m in s["by_condition"].items():
        d, model, cal = key.split("|")
        out.append(
            f"| {d} | {model} | {CAL_LABELS.get(cal, cal)} | {_ci(m['accuracy'], 1, True)} | {_ci(m['mean_confidence'], 1, True)} | "
            f"{_ci(m['ece'], 1, True)} | {_ci(m['mce'], 1, True)} | {_ci(m['brier'], 4)} | {_ci(m['nll'], 3)} |"
        )
    truth = [(k, m) for k, m in s["by_condition"].items() if "mae_true_p" in m]
    if truth:
        out += ["", "### Synthetic payments: distance to the known true probability", "",
                "| Model | Calibrator | Mean abs. error to true p | Brier | Bayes Brier (irreducible) |", "|---|---|---|---|---|"]  # fmt: skip
        for k, m in truth:
            _, model, cal = k.split("|")
            out.append(
                f"| {model} | {CAL_LABELS.get(cal, cal)} | {_ci(m['mae_true_p'], 4)} | {_ci(m['brier'], 4)} | {_ci(m['brier_true_p'], 4)} |"
            )
    out += ["", "### Does post-hoc calibration help? (paired over seeds, calibrated minus uncalibrated; sign-flip test)", "",
            "| Domain | Model | Metric | Calibrator | Difference | 95% CI | p |", "|---|---|---|---|---|---|---|"]  # fmt: skip
    for p in s["pairwise"]:
        scale, digits = (100, 2) if p["metric"] == "ece" else (1, 4)
        unit = " pp" if p["metric"] == "ece" else ""
        out.append(
            f"| {p['domain']} | {p['model']} | {p['metric'].upper() if p['metric'] == 'ece' else 'Brier'} | {CAL_LABELS.get(p['a'], p['a'])} | "
            f"{p['diff'] * scale:+.{digits}f}{unit} | [{p['ci_low'] * scale:+.{digits}f}, {p['ci_high'] * scale:+.{digits}f}] | {_p(p['p_value'])} |"
        )
    return [*out, ""]


def _e2_tables(s: dict[str, Any]) -> list[str]:
    out = ["## E2: Four oversight regimes", "", _prov(s), "",
           "Means over seeds with 95% bootstrap CIs. Loss is the cost of wrong final decisions per 1,000 cases in the "
           "domain's stake units. Decision time is from arrival to final decision (0 for autonomous decisions).", ""]  # fmt: skip
    pol = s.get("policies", {})
    for domain, dd in s["domains"].items():
        r = dd["regimes"]
        p = pol.get(domain, {})
        out += [f"### {DOMAIN_LABELS.get(domain, domain)}", ""]
        if p:
            out += [f"Policy `{p['id']}` v{p['version']} (hash `{p['hash']}`).", ""]
        out += ["| Regime | Accuracy (%) | Loss / 1,000 | Share to a human (%) | Reviewer hours / 1,000 | Decision min, median | Decision min, p95 | High-stake errors / 1,000 |",
                "|---|---|---|---|---|---|---|---|"]  # fmt: skip
        for g in REGIMES:
            m = r[g]
            out.append(
                f"| {REGIME_LABELS[g]} | {_ci(m['accuracy'], 1, True)} | {_ci(m['loss_per_1000'], 0)} | {_ci(m['share_human'], 1, True)} | "
                f"{_ci(m['reviewer_hours_per_1000'], 1)} | {_ci(m['decision_minutes_median'], 1)} | {_ci(m['decision_minutes_p95'], 1)} | "
                f"{_ci(m.get('high_stake_errors_per_1000'), 2)} |"
            )
        ai_loss = r["ai_only"]["loss_per_1000"]["mean"]
        eff = []
        for g in ("human_only", "blanket_approval", "risk_adaptive"):
            hours = r[g]["reviewer_hours_per_1000"]["mean"]
            if ai_loss is not None and hours:
                eff.append(
                    f"{REGIME_LABELS[g]} {(ai_loss - r[g]['loss_per_1000']['mean']) / hours:,.1f}"
                )
        if eff:
            out += ["", "Loss avoided per reviewer hour relative to AI only (ratio of seed means; negative = oversight added loss): " + "; ".join(eff) + "."]  # fmt: skip
        out += ["", "Oversight behaviour on cases where a reviewer saw the AI's decision:", "",
                "| Regime | Override rate (%) | Override precision (%) | Automation bias (%) | Appropriate reliance (%) | Reviewer utilisation (%) |",
                "|---|---|---|---|---|---|"]  # fmt: skip
        for g in ("blanket_approval", "risk_adaptive"):
            m = r[g]
            out.append(
                f"| {REGIME_LABELS[g]} | {_ci(m['override_rate'], 1, True)} | {_ci(m['override_precision'], 1, True)} | "
                f"{_ci(m['automation_bias_rate'], 1, True)} | {_ci(m['appropriate_reliance'], 1, True)} | {_ci(m['utilisation'], 1, True)} |"
            )
        out += ["", "Error attribution (wrong final decisions per 1,000 cases, by cause):", "",
                "| Regime | Autonomous AI error | Reviewer accepted a wrong AI decision | Harmful override | Unaided human error |",
                "|---|---|---|---|---|"]  # fmt: skip
        for g in REGIMES:
            e = r[g]["errors"]
            out.append(
                f"| {REGIME_LABELS[g]} | {_ci(e['autonomous_ai_error'], 1)} | {_ci(e['accepted_wrong_ai'], 1)} | "
                f"{_ci(e['harmful_override'], 1)} | {_ci(e['unaided_human_error'], 1)} |"
            )
        ra = r["risk_adaptive"]
        if "tier_share" in ra:
            tiers = ra["tier_share"]
            ebt = ra["error_by_tier"]
            out += ["", "Risk-adaptive routing by tier:", "", "| Tier | Share of cases (%) | Final error rate in tier (%) |", "|---|---|---|"]  # fmt: skip
            for t in tiers:
                out.append(f"| {t} | {_ci(tiers[t], 1, True)} | {_ci(ebt.get(t), 1, True)} |")
            fired = ra.get("rules_fired_share", {})
            if fired:
                out += ["", "Policy rules fired (share of cases): " + ", ".join(f"`{k}` {v * 100:.1f}%" for k, v in sorted(fired.items())) + "."]  # fmt: skip
        out += ["", "Group breakdown, risk-adaptive regime (error-analysis only; groups are not used for routing):", "",
                "| Group | Level | Final error rate (%) | Share to a human (%) |", "|---|---|---|---|"]  # fmt: skip
        for g, levels in ra["groups"].items():
            for lv, v in levels.items():
                out.append(
                    f"| {g} | {lv} | {_ci(v['error_rate'], 1, True)} | {_ci(v['share_human'], 1, True)} |"
                )
        out += ["", "Paired comparisons (A minus B over seeds; sign-flip test, Holm-adjusted within each metric and domain):", "",
                "| Metric | A | B | A - B | 95% CI | p (Holm) |", "|---|---|---|---|---|---|"]  # fmt: skip
        for p in dd["pairwise"]:
            scale, digits = (100, 2) if p["metric"] == "accuracy" else (1, 1)
            unit = " pp" if p["metric"] == "accuracy" else ""
            out.append(
                f"| {p['metric']} | {REGIME_LABELS[p['a']]} | {REGIME_LABELS[p['b']]} | {p['diff'] * scale:+.{digits}f}{unit} | "
                f"[{p['ci_low'] * scale:+.{digits}f}, {p['ci_high'] * scale:+.{digits}f}] | {_p(p['p_holm'])} |"
            )
        out.append("")
    return out


def _e3_tables(s: dict[str, Any]) -> list[str]:
    q = s["matched_share"]
    out = ["## E3: Loss-workload frontier and routing ablations", "", _prov(s), "",
           f"Each router sends its top share of cases (by its score, threshold set on the calibration split) to `{s['mode']}`; "
           "the rest run autonomously. Loss per 1,000 cases, mean [95% CI].", ""]  # fmt: skip
    for domain, dd in s["domains"].items():
        curves = dd["curves"]
        shares = [c["target_share"] for c in curves["expected_cost"]]
        out += [f"### {DOMAIN_LABELS.get(domain, domain)}", "",
                "| Router | " + " | ".join(f"{x * 100:g}%" for x in shares) + " |", "|---|" + "---|" * len(shares)]  # fmt: skip
        for router in ROUTERS:
            cells = [_num(c["loss_per_1000"]["mean"], 0) for c in curves[router]]
            out.append(f"| {ROUTER_LABELS[router]} | " + " | ".join(cells) + " |")
        pp = dd["policy"]
        out += ["", f"Configured policy: loss {_ci(pp['loss_per_1000'], 0)} per 1,000 with {_ci(pp['share_human'], 1, True)}% of cases to a human "
                f"and {_ci(pp['reviewer_hours_per_1000'], 1)} reviewer hours per 1,000.", "",
                f"At a matched {q * 100:g}% review share (expected cost, calibrated, minus each alternative; Holm-adjusted):", "",
                "| Alternative router | Loss difference / 1,000 | 95% CI | p (Holm) |", "|---|---|---|---|"]  # fmt: skip
        for p in dd["matched"]:
            out.append(
                f"| {ROUTER_LABELS[p['b']]} | {p['diff']:+.1f} | [{p['ci_low']:+.1f}, {p['ci_high']:+.1f}] | {_p(p['p_holm'])} |"
            )
        out.append("")
    return out


def _e4_tables(s: dict[str, Any]) -> list[str]:
    out = ["## E4: Sensitivity to reviewer assumptions", "", _prov(s), "",
           "One parameter varies at a time; others stay at their defaults. Loss per 1,000 cases (mean over seeds). "
           "The last columns compare risk-adaptive oversight with the alternatives, paired over seeds (negative = adaptive loses less).", ""]  # fmt: skip
    for param, per_domain in s["axes"].items():
        out += [f"### `{param}`", "",
                "| Domain | Value | " + " | ".join(REGIME_LABELS[g] for g in REGIMES) + " | Lowest loss | Adaptive - AI only | Adaptive - blanket |",
                "|---|---|" + "---|" * (len(REGIMES) + 3)]  # fmt: skip
        for domain, rows in per_domain.items():
            for row in rows:
                cells = [_num(row[g]["loss_per_1000"]["mean"], 0) for g in REGIMES]
                a_ai, a_bl = row["adaptive_vs_ai_only"], row["adaptive_vs_blanket_approval"]
                out.append(
                    f"| {domain} | {row['value']:g} | "
                    + " | ".join(cells)
                    + f" | {REGIME_LABELS[row['lowest_loss_regime']]} | "
                    f"{a_ai['diff']:+.0f} (p {_p(a_ai['p_value'])}) | {a_bl['diff']:+.0f} (p {_p(a_bl['p_value'])}) |"
                )
        out.append("")
    return out


def _e5_tables(s: dict[str, Any]) -> list[str]:
    out = ["## E5: Distribution shift (synthetic payments)", "", _prov(s), "",
           "The agent, calibrator and policy are fitted before the shift; the test stream comes from the shifted generator.", ""]  # fmt: skip
    for kind, rows in s["shifts"].items():
        out += [f"### {kind.capitalize()} shift", "",
                "| Level | AI accuracy (%) | Mean confidence (%) | ECE (pp) | Autonomous share (%) | "
                + " | ".join(f"Loss: {REGIME_LABELS[g]}" for g in REGIMES) + " | Reviewer h / 1,000 (adaptive) |",
                "|---|---|---|---|---|" + "---|" * (len(REGIMES) + 1)]  # fmt: skip
        for row in rows:
            out.append(
                f"| {row['level']:g} | {_ci(row['ai_accuracy'], 1, True)} | {_ci(row['mean_confidence'], 1, True)} | {_ci(row['ece'], 1, True)} | "
                f"{_ci(row['autonomous_share'], 1, True)} | "
                + " | ".join(_ci(row[g]["loss_per_1000"], 0) for g in REGIMES)
                + f" | {_ci(row['risk_adaptive']['reviewer_hours_per_1000'], 1)} |"
            )
        out.append("")
    return out


# --- figures -----------------------------------------------------------------------------------
def _setup() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import logging

    import matplotlib.pyplot as plt

    # Geist is the console's font; it is rarely installed system-wide, so fall back quietly.
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    plt.rcParams.update({
        "font.family": ["Geist", "Inter", "DejaVu Sans"], "font.size": 9, "text.color": INK,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "svg.fonttype": "none",
        "svg.hashsalt": "governance", "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "legend.frameon": False,
    })  # fmt: skip
    return plt


def _save(plt: Any, fig: Any, path: Path) -> Path:
    fig.savefig(path, metadata={"Date": None})
    plt.close(fig)
    return path


def _fig_e1(plt: Any, s: dict[str, Any], out: Path) -> Path:
    domains = list(DOMAIN_LABELS)
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), sharey=True)
    for ax, d in zip(axes, domains, strict=True):
        ax.plot([0.5, 1], [0.5, 1], color=REFERENCE, lw=1, ls="--", label="perfect calibration")
        for cal, color in (("none", SERIES[1]), ("isotonic", SERIES[0])):
            bins = s["reliability"].get(f"{d}|gbm|{cal}")
            if not bins:
                continue
            ece = s["by_condition"][f"{d}|gbm|{cal}"]["ece"]["mean"] * 100
            ax.plot(
                [b["conf"] for b in bins],
                [b["acc"] for b in bins],
                "-o",
                color=color,
                lw=2,
                ms=4.5,
                mec=SURFACE,
                mew=1,
                label=f"{CAL_LABELS[cal]} (ECE {ece:.1f} pp)",
            )
        ax.set_title(DOMAIN_LABELS[d], loc="left", fontsize=9.5, color=INK)
        ax.set_xlim(0.48, 1.01)
        ax.set_ylim(0.3, 1.01)
        ax.set_xlabel("decision confidence")
        ax.legend(loc="upper left", fontsize=8)
    axes[0].set_ylabel("observed accuracy")
    fig.suptitle(
        "E1: reliability of the gradient-boosting agent, pooled over seeds (15 equal-mass bins)",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    return _save(plt, fig, out / "e1_reliability.svg")


def _fig_e2(plt: Any, s: dict[str, Any], out: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, (d, dd) in zip(axes, s["domains"].items(), strict=True):
        for g in REGIMES:
            m = dd["regimes"][g]
            x, y = m["reviewer_hours_per_1000"], m["loss_per_1000"]
            c = REGIME_COLOR[g]
            ax.plot([x["mean"], x["mean"]], [y["ci_low"], y["ci_high"]], color=c, lw=2)
            ax.plot([x["ci_low"], x["ci_high"]], [y["mean"], y["mean"]], color=c, lw=2)
            ax.plot(
                x["mean"],
                y["mean"],
                "o",
                color=c,
                ms=7,
                mec=SURFACE,
                mew=1.5,
                label=REGIME_LABELS[g],
            )
        ax.set_title(DOMAIN_LABELS.get(d, d), loc="left", fontsize=9.5, color=INK)
        ax.set_xlabel("reviewer hours per 1,000 cases")
        ax.margins(x=0.08, y=0.15)
    axes[0].set_ylabel("loss per 1,000 cases")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8.5)
    fig.suptitle(
        "E2: loss vs human workload by regime (mean and 95% CI over seeds)",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return _save(plt, fig, out / "e2_regimes.svg")


def _fig_e3(plt: Any, s: dict[str, Any], out: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, (d, dd) in zip(axes, s["domains"].items(), strict=True):
        for router in ROUTERS:
            pts = dd["curves"][router]
            xs = [p["share_human"]["mean"] for p in pts]
            ys = [p["loss_per_1000"]["mean"] for p in pts]
            ax.fill_between(
                xs,
                [p["loss_per_1000"]["ci_low"] for p in pts],
                [p["loss_per_1000"]["ci_high"] for p in pts],
                color=ROUTER_COLOR[router],
                alpha=0.1,
                lw=0,
            )
            ax.plot(
                xs,
                ys,
                "-" if router != "random" else "--",
                color=ROUTER_COLOR[router],
                lw=2,
                label=ROUTER_LABELS[router],
            )
        pp = dd["policy"]
        ax.plot(
            pp["share_human"]["mean"],
            pp["loss_per_1000"]["mean"],
            "s",
            color=INK,
            ms=7,
            mec=SURFACE,
            mew=1.5,
            label=ROUTER_LABELS["policy"],
        )
        ax.set_title(DOMAIN_LABELS.get(d, d), loc="left", fontsize=9.5, color=INK)
        ax.set_xlabel("share of cases sent to a human")
        ax.set_xlim(-0.02, 1.02)
    axes[0].set_ylabel("loss per 1,000 cases")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=6, fontsize=8)
    fig.suptitle(
        "E3: loss-workload frontier by routing score (review mode; mean and 95% CI over seeds)",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return _save(plt, fig, out / "e3_frontier.svg")


def _fig_e4(plt: Any, s: dict[str, Any], out: Path) -> Path | None:
    axis = s["axes"].get("automation_bias_review")
    if not axis:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3))
    for ax, (d, rows) in zip(axes, axis.items(), strict=True):
        xs = [r["value"] for r in rows]
        for g in REGIMES:
            ys = [r[g]["loss_per_1000"]["mean"] for r in rows]
            ax.fill_between(
                xs,
                [r[g]["loss_per_1000"]["ci_low"] for r in rows],
                [r[g]["loss_per_1000"]["ci_high"] for r in rows],
                color=REGIME_COLOR[g],
                alpha=0.1,
                lw=0,
            )
            ax.plot(xs, ys, "-o", color=REGIME_COLOR[g], lw=2, ms=4.5, label=REGIME_LABELS[g])
        ax.set_title(DOMAIN_LABELS.get(d, d), loc="left", fontsize=9.5, color=INK)
        ax.set_xlabel("reviewer deference to the AI (review mode)")
        ax.set_xticks(xs)
    axes[0].set_ylabel("loss per 1,000 cases")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8.5)
    fig.suptitle(
        "E4: sensitivity of loss to automation bias in review (mean and 95% CI over seeds)",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    return _save(plt, fig, out / "e4_automation_bias.svg")


def _fig_e5(plt: Any, s: dict[str, Any], out: Path) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3))
    for kind, ls in (("covariate", "-"), ("concept", "--")):
        rows = s["shifts"][kind]
        xs = [r["level"] for r in rows]
        axes[0].plot(
            xs,
            [r["ece"]["mean"] * 100 for r in rows],
            ls,
            marker="o",
            color=SERIES[0],
            lw=2,
            ms=4.5,
            label=f"{kind} shift",
        )
        axes[1].plot(
            xs,
            [r["autonomous_share"]["mean"] * 100 for r in rows],
            ls,
            marker="o",
            color=SERIES[0],
            lw=2,
            ms=4.5,
            label=f"{kind} shift",
        )
        for g in ("ai_only", "risk_adaptive"):
            axes[2].plot(
                xs,
                [r[g]["loss_per_1000"]["mean"] for r in rows],
                ls,
                marker="o",
                color=REGIME_COLOR[g],
                lw=2,
                ms=4.5,
                label=f"{REGIME_LABELS[g]}, {kind}",
            )
    axes[0].set_title("ECE of decision confidence (pp)", loc="left", fontsize=9.5)
    axes[1].set_title("Cases decided autonomously (%)", loc="left", fontsize=9.5)
    axes[2].set_title("Loss per 1,000 cases", loc="left", fontsize=9.5)
    for ax in axes:
        ax.set_xlabel("shift level")
        ax.set_xticks([r["level"] for r in s["shifts"]["covariate"]])
        ax.legend(fontsize=7.5, loc="best")
    fig.suptitle(
        "E5: what shift does to calibration, routing and loss (synthetic payments, mean over seeds)",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout()
    return _save(plt, fig, out / "e5_shift.svg")


def generate_report(root: Path) -> list[Path]:
    s = {e: _latest(root, e) for e in EXPERIMENTS}
    lines = ["# Generated results", "",
             "Produced by `governance report` from the latest completed run of each experiment. Do not edit by hand; "
             "every table names the run and commit it came from.", ""]  # fmt: skip
    sections = [
        ("e1_calibration", "E1: Calibration of decision confidence", _e1_tables),
        ("e2_regimes", "E2: Four oversight regimes", _e2_tables),
        ("e3_frontier", "E3: Loss-workload frontier and routing ablations", _e3_tables),
        ("e4_sensitivity", "E4: Sensitivity to reviewer assumptions", _e4_tables),
        ("e5_shift", "E5: Distribution shift (synthetic payments)", _e5_tables),
    ]
    for exp, title, fn in sections:
        data = s[exp]
        lines += fn(data) if data else _pending(title, exp)
    lines += ["## Human-subject study", "",
              "Status: pending. Trust and reviewer behaviour above come from a simulated reviewer with stated parameters; "
              "no study with real reviewers has been run (see docs/PLAN.md).", ""]  # fmt: skip
    out = root / "research" / "generated" / "results.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    written = [out]

    plt = _setup()
    fig_dir = root / "research" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    figures = (
        ("e1_calibration", _fig_e1),
        ("e2_regimes", _fig_e2),
        ("e3_frontier", _fig_e3),
        ("e4_sensitivity", _fig_e4),
        ("e5_shift", _fig_e5),
    )
    for exp, fig_fn in figures:
        data = s[exp]
        if data:
            path = fig_fn(plt, data, fig_dir)
            if path is not None:
                written.append(path)
    return written
