"""API and store: queue seeding, auth on writes, tier rules, label hiding and the audit chain."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from governance.api.app import create_app, parse_reviewer_tokens

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "alice-secret-token-123"


@pytest.fixture(scope="module")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("db") / "governance.db"


@pytest.fixture(scope="module")
def client(db_path: Path) -> TestClient:
    mp = pytest.MonkeyPatch()
    mp.setenv("GOVERNANCE_REVIEWER_TOKENS", f"alice:{TOKEN}")
    mp.delenv("GOVERNANCE_API_TOKEN", raising=False)
    app = create_app(ROOT, db_path=db_path, seed_domains=("payments",), seed_cases=150)
    mp.undo()
    return TestClient(app)


def _auth() -> dict[str, str]:
    return {"X-Reviewer-Token": TOKEN}


def test_health_meta_and_headers(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["writes_enabled"] is True
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert {t for t in client.get("/api/meta").json()["tiers"]} == {
        "autonomous",
        "review",
        "approval",
    }


def test_queue_is_ordered_and_hides_labels(client: TestClient) -> None:
    q = client.get("/api/queue", params={"domain": "payments"}).json()
    assert q, "seeded queue should have pending cases"
    tiers = [c["tier"] for c in q]
    assert set(tiers) <= {"review", "approval"}
    # Mandatory approvals come first, then by expected cost.
    first_review = tiers.index("review") if "review" in tiers else len(tiers)
    assert all(t == "approval" for t in tiers[:first_review])
    reviews = [c["expected_cost"] for c in q if c["tier"] == "review"]
    assert reviews == sorted(reviews, reverse=True)
    detail = client.get(f"/api/cases/{q[0]['id']}").json()
    assert "truth" not in detail and "correct" not in detail
    assert detail["routing"]["policy_hash"] and detail["audit"][0]["action"] == "routed"


def test_autonomous_cases_are_executed_and_logged(client: TestClient) -> None:
    auto = client.get("/api/queue", params={"status": "auto_executed", "limit": 5}).json()
    assert auto and all(c["final_decision"] == c["ai_decision"] for c in auto)
    detail = client.get(f"/api/cases/{auto[0]['id']}").json()
    assert [e["action"] for e in reversed(detail["audit"])] == ["routed", "executed"]


def test_writes_need_a_reviewer_token(client: TestClient) -> None:
    case = client.get("/api/queue", params={"tier": "review", "limit": 1}).json()[0]
    r = client.post(f"/api/cases/{case['id']}/decision", json={"action": "accept"})
    assert r.status_code == 401
    r = client.post(
        f"/api/cases/{case['id']}/decision",
        json={"action": "accept"},
        headers={"X-Reviewer-Token": "wrong-token-0000000"},
    )
    assert r.status_code == 401
    assert client.get("/api/reviewer", headers=_auth()).json() == {"reviewer": "reviewer:alice"}
    assert client.get("/api/reviewer").status_code == 401


def test_review_decision_flow(client: TestClient) -> None:
    case = client.get("/api/queue", params={"tier": "review", "limit": 1}).json()[0]
    # Override without a reason is rejected by validation.
    r = client.post(
        f"/api/cases/{case['id']}/decision", json={"action": "override"}, headers=_auth()
    )
    assert r.status_code == 422
    # "approve" is reserved for the approval tier.
    r = client.post(
        f"/api/cases/{case['id']}/decision",
        json={"action": "approve", "reason": "looks fine to me"},
        headers=_auth(),
    )
    assert r.status_code == 409
    r = client.post(f"/api/cases/{case['id']}/decision", json={"action": "accept"}, headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "decided" and body["decided_by"] == "reviewer:alice"
    assert body["final_decision"] == body["ai_decision"] and "truth" in body
    # A second decision on the same case conflicts.
    r = client.post(f"/api/cases/{case['id']}/decision", json={"action": "accept"}, headers=_auth())
    assert r.status_code == 409


def test_approval_needs_justification_and_override_flips(client: TestClient) -> None:
    q = client.get("/api/queue", params={"tier": "approval", "limit": 2}).json()
    if len(q) < 2:
        pytest.skip("seeded stream has fewer than two approval cases")
    r = client.post(
        f"/api/cases/{q[0]['id']}/decision", json={"action": "approve"}, headers=_auth()
    )
    assert r.status_code == 409 and "justification" in r.json()["detail"]
    r = client.post(
        f"/api/cases/{q[0]['id']}/decision",
        json={"action": "approve", "reason": "Vendor verified by phone"},
        headers=_auth(),
    )
    assert r.status_code == 200 and r.json()["reason"] == "Vendor verified by phone"
    r = client.post(
        f"/api/cases/{q[1]['id']}/decision",
        json={"action": "override", "reason": "Bank details changed yesterday"},
        headers=_auth(),
    )
    body = r.json()
    assert r.status_code == 200 and body["final_decision"] != body["ai_decision"]


def test_stats_and_audit_chain(client: TestClient, db_path: Path) -> None:
    s = client.get("/api/stats").json()
    assert s["human_decisions"] >= 1
    v = client.get("/api/audit/verify").json()
    assert v["valid"] is True and v["events"] > 150
    # Tampering with any stored event breaks verification at that event.
    con = sqlite3.connect(db_path)
    seq = con.execute("SELECT seq FROM audit ORDER BY seq LIMIT 1 OFFSET 5").fetchone()[0]
    con.execute("UPDATE audit SET payload = '{\"tampered\":true}' WHERE seq = ?", (seq,))
    con.commit()
    con.close()
    v = client.get("/api/audit/verify").json()
    assert v["valid"] is False and v["first_bad_seq"] == seq


def test_input_validation(client: TestClient) -> None:
    assert client.get("/api/queue", params={"domain": "../etc"}).status_code == 422
    assert client.get("/api/cases/..%2F..%2Fetc").status_code in {400, 404}
    assert client.get("/api/experiments/not_an_experiment").status_code == 404


def test_writes_disabled_without_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOVERNANCE_REVIEWER_TOKENS", raising=False)
    app = create_app(ROOT, db_path=tmp_path / "g.db", seed_domains=("payments",), seed_cases=40)
    c = TestClient(app)
    case = c.get("/api/queue", params={"limit": 1}).json()[0]
    r = c.post(f"/api/cases/{case['id']}/decision", json={"action": "accept"}, headers=_auth())
    assert r.status_code == 403


def test_read_token_and_token_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVERNANCE_API_TOKEN", "read-token-abcdefgh")
    app = create_app(ROOT, db_path=tmp_path / "g.db", seed_cases=0)
    c = TestClient(app)
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/meta").status_code == 401
    assert (
        c.get("/api/meta", headers={"Authorization": "Bearer read-token-abcdefgh"}).status_code
        == 200
    )
    with pytest.raises(ValueError):
        parse_reviewer_tokens("alice:short")
    assert parse_reviewer_tokens(" a:0123456789abcdef , b:fedcba9876543210 ") == {
        "0123456789abcdef": "a",
        "fedcba9876543210": "b",
    }
