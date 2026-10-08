"""Decision domains: real tabular datasets (UCI German Credit, UCI Adult) and a synthetic payment-
approval domain with a known generative model.

Every domain is reduced to the same shape: a binary decision where ``y = 1`` means the *positive*
action (approve / grant) is the correct one, a per-case stake, an asymmetric cost of each error type,
display features, group attributes for error analysis, and (synthetic only) the true probability.
"""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"

# SHA-256 of the committed raw files; loading fails loudly if a file differs.
CHECKSUMS = {
    "german.csv": "ec12a88b9fc14d74ba646ea0410cf7ff4533bec2eb61652f8ad76796bbfec017",
    "adult-all.csv": "21e0ea2f925a00338929a8c86c27354c72ac1c79819bcca81c7d91c3d64218c2",
}


@dataclass
class Domain:
    """A decision domain.

    ``cost_false_approve`` / ``cost_false_decline`` multiply the stake to give the cost of each
    error; the agent and the router use them, the simulation uses them to score outcomes.
    """

    name: str
    title: str
    positive_action: str
    negative_action: str
    stake_unit: str
    features: list[dict[str, Any]]
    numeric: list[str]
    categorical: list[str]
    y: np.ndarray
    stake: np.ndarray
    groups: dict[str, np.ndarray]
    cost_false_approve: float
    cost_false_decline: float
    true_p: np.ndarray | None = None
    notes: dict[str, str] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.y)

    def error_cost(self, decision: np.ndarray, y: np.ndarray, stake: np.ndarray) -> np.ndarray:
        """Cost of each final decision (0 when correct)."""
        false_approve = (decision == 1) & (y == 0)
        false_decline = (decision == 0) & (y == 1)
        return stake * (
            false_approve * self.cost_false_approve + false_decline * self.cost_false_decline
        )

    def cost_if_wrong(self, decision: np.ndarray, stake: np.ndarray) -> np.ndarray:
        """Cost incurred if ``decision`` turns out to be wrong."""
        return stake * np.where(decision == 1, self.cost_false_approve, self.cost_false_decline)


def _verify(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != CHECKSUMS[path.name]:
        raise ValueError(f"{path} checksum mismatch: {digest} (expected {CHECKSUMS[path.name]})")


# --- UCI Statlog German Credit ----------------------------------------------------------------
_GERMAN_COLUMNS = [
    "checking_status", "duration_months", "credit_history", "purpose", "credit_amount",
    "savings", "employment_since", "installment_rate", "personal_status_sex", "other_debtors",
    "residence_since", "property", "age", "other_installment_plans", "housing",
    "existing_credits", "job", "people_liable", "telephone", "foreign_worker", "class",
]  # fmt: skip
_GERMAN_NUMERIC = [
    "duration_months", "credit_amount", "installment_rate", "residence_since", "age",
    "existing_credits", "people_liable",
]  # fmt: skip
_GERMAN_CODES = {
    "checking_status": {"A11": "< 0 DM", "A12": "0-200 DM", "A13": ">= 200 DM", "A14": "no account"},
    "credit_history": {"A30": "no credits / all paid", "A31": "all paid at this bank",
                       "A32": "existing paid duly", "A33": "past delays", "A34": "critical account"},
    "purpose": {"A40": "car (new)", "A41": "car (used)", "A42": "furniture", "A43": "radio/TV",
                "A44": "appliances", "A45": "repairs", "A46": "education", "A47": "vacation",
                "A48": "retraining", "A49": "business", "A410": "other"},
    "savings": {"A61": "< 100 DM", "A62": "100-500 DM", "A63": "500-1000 DM", "A64": ">= 1000 DM",
                "A65": "unknown / none"},
    "employment_since": {"A71": "unemployed", "A72": "< 1 year", "A73": "1-4 years",
                         "A74": "4-7 years", "A75": ">= 7 years"},
    "personal_status_sex": {"A91": "male: divorced/separated", "A92": "female: div/sep/married",
                            "A93": "male: single", "A94": "male: married/widowed",
                            "A95": "female: single"},
    "other_debtors": {"A101": "none", "A102": "co-applicant", "A103": "guarantor"},
    "property": {"A121": "real estate", "A122": "savings/insurance", "A123": "car/other",
                 "A124": "unknown / none"},
    "other_installment_plans": {"A141": "bank", "A142": "stores", "A143": "none"},
    "housing": {"A151": "rent", "A152": "own", "A153": "for free"},
    "job": {"A171": "unemployed/unskilled non-resident", "A172": "unskilled resident",
            "A173": "skilled employee", "A174": "management/self-employed"},
    "telephone": {"A191": "none", "A192": "yes"},
    "foreign_worker": {"A201": "yes", "A202": "no"},
}  # fmt: skip


def load_german(raw_dir: Path = RAW_DIR) -> Domain:
    path = raw_dir / "german.csv"
    _verify(path)
    with path.open() as f:
        rows = [dict(zip(_GERMAN_COLUMNS, r, strict=True)) for r in csv.reader(f) if r]
    features: list[dict[str, Any]] = []
    for r in rows:
        feat: dict[str, Any] = {}
        for k, v in r.items():
            if k == "class":
                continue
            feat[k] = float(v) if k in _GERMAN_NUMERIC else _GERMAN_CODES[k].get(v, v)
        features.append(feat)
    y = np.array([1 if r["class"] == "1" else 0 for r in rows])
    stake = np.array([float(r["credit_amount"]) for r in rows])
    sex = np.array(
        ["female" if r["personal_status_sex"] in {"A92", "A95"} else "male" for r in rows]
    )
    age = np.array([float(r["age"]) for r in rows])
    return Domain(
        name="credit",
        title="Credit approval (UCI German Credit)",
        positive_action="approve",
        negative_action="decline",
        stake_unit="DM",
        features=features,
        numeric=_GERMAN_NUMERIC,
        categorical=[c for c in _GERMAN_COLUMNS if c not in _GERMAN_NUMERIC and c != "class"],
        y=y,
        stake=stake,
        groups={"sex": sex, "age_band": np.where(age < 25, "under 25", "25 and over")},
        # The dataset's documented cost matrix: approving a bad credit costs 5, declining a good one 1.
        cost_false_approve=5.0,
        cost_false_decline=1.0,
        notes={
            "cost": "Cost matrix from the dataset documentation (5:1), scaled by credit amount."
        },
    )


# --- UCI Adult (Census Income) ----------------------------------------------------------------
_ADULT_COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num", "marital_status", "occupation",
    "relationship", "race", "sex", "capital_gain", "capital_loss", "hours_per_week",
    "native_country", "income",
]  # fmt: skip
_ADULT_NUMERIC = ["age", "education_num", "capital_gain", "capital_loss", "hours_per_week"]
_ADULT_CATEGORICAL = [
    "workclass", "education", "marital_status", "occupation", "relationship", "race", "sex",
    "native_country",
]  # fmt: skip


def load_adult(raw_dir: Path = RAW_DIR) -> Domain:
    path = raw_dir / "adult-all.csv"
    _verify(path)
    with path.open() as f:
        rows = [dict(zip(_ADULT_COLUMNS, r, strict=True)) for r in csv.reader(f) if r]
    features: list[dict[str, Any]] = []
    for r in rows:
        feat: dict[str, Any] = {}
        for k in _ADULT_NUMERIC:
            feat[k] = float(r[k])
        for k in _ADULT_CATEGORICAL:
            v = r[k].strip()
            feat[k] = "unknown" if v == "?" else v
        features.append(feat)
    # Positive action = grant eligibility for an income-tested programme (income <= 50K).
    y = np.array([1 if r["income"].strip().startswith("<=") else 0 for r in rows])
    return Domain(
        name="eligibility",
        title="Eligibility screening (UCI Adult)",
        positive_action="grant",
        negative_action="deny",
        stake_unit="cost units",
        features=features,
        numeric=_ADULT_NUMERIC,
        categorical=_ADULT_CATEGORICAL,
        y=y,
        stake=np.ones(len(rows)),
        groups={
            "sex": np.array([f["sex"] for f in features]),
            "race": np.array([f["race"] for f in features]),
        },
        # Assumption (stated in docs): wrongly denying an eligible applicant is three times as
        # costly as wrongly granting eligibility.
        cost_false_approve=1.0,
        cost_false_decline=3.0,
        notes={
            "cost": "Assumed costs: false denial 3, false grant 1 (unit stakes).",
            "framing": "Label is census income <= 50K (1994); the programme framing is a stand-in.",
        },
    )


# --- Synthetic payment approvals --------------------------------------------------------------
SYNTH_COEF = {
    "intercept": 2.6,
    "log_amount": -0.45,
    "vendor_age_years": 0.35,
    "vendor_risk_score": -1.6,
    "invoice_mismatch": -1.9,
    "new_bank_details": -1.4,
    "after_hours": -0.5,
}


def synthetic_true_p(feat: dict[str, Any], shift: float = 0.0) -> float:
    """True probability that approving the payment is correct (the payment is legitimate).

    ``shift`` > 0 is concept shift: the effect of changed bank details strengthens, which a model
    trained before the shift cannot know.
    """
    z = SYNTH_COEF["intercept"]
    z += SYNTH_COEF["log_amount"] * (math.log10(feat["amount"]) - 3.0)
    z += SYNTH_COEF["vendor_age_years"] * min(feat["vendor_age_years"], 10.0) / 3.0
    z += SYNTH_COEF["vendor_risk_score"] * feat["vendor_risk_score"]
    z += SYNTH_COEF["invoice_mismatch"] * feat["invoice_mismatch"]
    z += (SYNTH_COEF["new_bank_details"] - 1.5 * shift) * feat["new_bank_details"]
    z += SYNTH_COEF["after_hours"] * feat["after_hours"]
    return 1.0 / (1.0 + math.exp(-z))


def synthetic_features(rng: np.random.Generator, covariate_shift: float = 0.0) -> dict[str, Any]:
    """One payment request. ``covariate_shift`` > 0 moves mass toward riskier vendors and larger
    amounts (the feature distribution changes, the outcome model does not)."""
    regions = ("north", "south", "east", "west")
    risk = float(np.clip(rng.beta(2.0, 5.0) + 0.25 * covariate_shift * rng.random(), 0.0, 1.0))
    return {
        "amount": float(round(rng.lognormal(7.0 + 0.6 * covariate_shift, 1.1), 2)),
        "vendor_age_years": float(round(rng.exponential(4.0 * (1 - 0.4 * covariate_shift)), 2)),
        "vendor_risk_score": round(risk, 3),
        "invoice_mismatch": int(rng.random() < 0.08 + 0.08 * covariate_shift),
        "new_bank_details": int(rng.random() < 0.06 + 0.06 * covariate_shift),
        "after_hours": int(rng.random() < 0.15),
        "region": str(regions[int(rng.integers(0, 4))]),
    }


def make_synthetic(
    n: int = 20000, seed: int = 0, covariate_shift: float = 0.0, concept_shift: float = 0.0
) -> Domain:
    rng = np.random.default_rng(seed)
    features = [synthetic_features(rng, covariate_shift) for _ in range(n)]
    true_p = np.array([synthetic_true_p(f, concept_shift) for f in features])
    y = (rng.random(n) < true_p).astype(int)
    return Domain(
        name="payments",
        title="Payment approvals (synthetic)",
        positive_action="approve",
        negative_action="reject",
        stake_unit="currency units",
        features=features,
        numeric=["amount", "vendor_age_years", "vendor_risk_score"],
        categorical=["invoice_mismatch", "new_bank_details", "after_hours", "region"],
        y=y,
        stake=np.array([f["amount"] for f in features]),
        groups={"region": np.array([f["region"] for f in features])},
        # Approving a fraudulent payment loses the amount; rejecting a legitimate one costs
        # handling and supplier friction, assumed at 25% of the amount.
        cost_false_approve=1.0,
        cost_false_decline=0.25,
        true_p=true_p,
        notes={"cost": "Fraud loses the amount; a wrong rejection costs 25% of it (assumption)."},
    )


def load_domain(name: str, **kwargs: Any) -> Domain:
    if name == "credit":
        return load_german()
    if name == "eligibility":
        return load_adult()
    if name == "payments":
        return make_synthetic(**kwargs)
    raise ValueError(f"unknown domain '{name}' (credit, eligibility, payments)")


DOMAINS = ("credit", "eligibility", "payments")
