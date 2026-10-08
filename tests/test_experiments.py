from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from governance.experiments.runner import run_experiment
from governance.experiments.stats import aggregate, holm, paired_test

ROOT = Path(__file__).resolve().parents[1]


def test_stats() -> None:
    a = aggregate([1.0, 2.0, 3.0, None])
    assert a["mean"] == 2.0 and a["n"] == 3 and a["ci_low"] <= 2.0 <= a["ci_high"]
    assert aggregate([None])["mean"] is None
    t = paired_test([1.0] * 10, [0.0] * 10)
    assert t["diff"] == 1.0 and t["p_value"] < 0.01
    assert paired_test([1.0, -1.0] * 5, [0.0] * 10)["p_value"] > 0.5
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


@pytest.fixture(scope="module")
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("ws")
    shutil.copytree(ROOT / "configs", root / "configs")
    return root


def _cfg(root: Path, name: str, body: str) -> Path:
    p = root / "configs" / f"{name}.yaml"
    p.write_text(f"experiment: {name}\ndescription: test\nbase_seed: 3\nseeds: 2\n{body}")
    return p


def _summary(out: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((out / "summary.json").read_text())
    return data


def test_regimes_experiment_end_to_end(workspace: Path) -> None:
    out = run_experiment(
        _cfg(workspace, "t_regimes", "kind: regimes\ndomains: [payments]\n"), workspace, quiet=True
    )
    s = _summary(out)
    reg = s["domains"]["payments"]["regimes"]
    assert reg["ai_only"]["reviewer_hours_per_1000"]["mean"] == 0.0
    assert (
        reg["human_only"]["share_human"]["mean"] == 1.0
        and reg["blanket_approval"]["share_human"]["mean"] == 1.0
    )
    assert 0 < reg["risk_adaptive"]["share_human"]["mean"] < 1
    assert reg["risk_adaptive"]["tier_share"]["autonomous"]["mean"] > 0.5
    assert s["provenance"]["seeds"] == 2 and len(s["domains"]["payments"]["pairwise"]) == 18
    assert (workspace / "results" / "t_regimes" / "LATEST").read_text().strip() == out.name


def test_frontier_and_calibration_experiments(workspace: Path) -> None:
    out = run_experiment(
        _cfg(
            workspace,
            "t_frontier",
            "kind: frontier\ndomains: [payments]\nfrontier_shares: [0.0, 0.2, 1.0]\n",
        ),
        workspace,
        quiet=True,
    )
    d = _summary(out)["domains"]["payments"]
    ec = d["curves"]["expected_cost"]
    assert ec[0]["share_human"]["mean"] == 0.0 and ec[-1]["share_human"]["mean"] == 1.0
    assert (
        abs(ec[1]["share_human"]["mean"] - 0.2) < 0.05
    )  # calibration-split threshold ~ hits target
    assert {m["b"] for m in d["matched"]} == {
        "expected_cost_uncalibrated",
        "confidence_only",
        "stake_only",
        "random",
    }
    out = run_experiment(
        _cfg(workspace, "t_cal", "kind: calibration\ndomains: [payments]\nmodels: [logreg]\n"),
        workspace,
        quiet=True,
    )
    s = _summary(out)
    assert set(s["by_condition"]) == {
        "payments|logreg|none",
        "payments|logreg|platt",
        "payments|logreg|isotonic",
    }
    assert "mae_true_p" in s["by_condition"]["payments|logreg|none"]


def test_sensitivity_and_shift_experiments(workspace: Path) -> None:
    body = "kind: sensitivity\ndomains: [payments]\nseeds: 1\nsweeps:\n  - {param: automation_bias_review, values: [0.0, 0.9]}\n  - {param: reviewers, values: [2]}\n"
    s = _summary(run_experiment(_cfg(workspace, "t_sens", body), workspace, quiet=True))
    rows = s["axes"]["automation_bias_review"]["payments"]
    # Automation bias changes what reviewers decide, not which cases they see or how long they take.
    hours = [r["risk_adaptive"]["reviewer_hours_per_1000"]["mean"] for r in rows]
    assert hours[0] == pytest.approx(hours[1])
    assert (
        rows[0]["ai_only"]["loss_per_1000"]["mean"] == rows[1]["ai_only"]["loss_per_1000"]["mean"]
    )
    s = _summary(
        run_experiment(
            _cfg(workspace, "t_shift", "kind: shift\nseeds: 1\nshift_levels: [0.0, 1.0]\n"),
            workspace,
            quiet=True,
        )
    )
    cov = s["shifts"]["covariate"]
    assert len(cov) == 2 and cov[0]["ece"]["mean"] is not None
