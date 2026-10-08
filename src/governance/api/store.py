"""SQLite store for the live review queue and its hash-chained audit log.

Every state change (a case routed, executed autonomously, accepted, approved or overridden) is an
audit event. Each event stores the SHA-256 of its canonical JSON together with the previous event's
hash, so deleting, reordering or editing any past event breaks verification from that point on.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GENESIS = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    seq INTEGER NOT NULL,
    tier TEXT NOT NULL,
    status TEXT NOT NULL,              -- pending | decided | auto_executed
    priority REAL NOT NULL,
    created_at TEXT NOT NULL,
    routing TEXT NOT NULL,             -- JSON audit_record() of the routing decision
    features TEXT NOT NULL,            -- JSON display features
    explanation TEXT NOT NULL,         -- JSON local evidence
    ai_decision TEXT NOT NULL,
    final_decision TEXT,
    truth TEXT NOT NULL,               -- simulation ground truth; never sent before a decision
    decided_by TEXT,
    decided_at TEXT,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS cases_queue ON cases(status, tier, priority);
CREATE TABLE IF NOT EXISTS audit (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    case_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_case ON audit(case_id);
"""


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def event_hash(prev_hash: str, ts: str, case_id: str, actor: str, action: str, payload: str) -> str:
    blob = json.dumps(
        [prev_hash, ts, case_id, actor, action, payload], separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(blob.encode()).hexdigest()


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # One connection shared by the server's worker threads: every statement, read or write,
        # runs under this lock so a read never observes another thread's open transaction.
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def _q(self, sql: str, args: tuple[Any, ...] | list[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    def _append(
        self, db: sqlite3.Connection, case_id: str, actor: str, action: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        row = db.execute("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else GENESIS
        ts = _now()
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        h = event_hash(prev, ts, case_id, actor, action, body)
        db.execute(
            "INSERT INTO audit (ts, case_id, actor, action, payload, prev_hash, hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, case_id, actor, action, body, prev, h),
        )
        return {"ts": ts, "actor": actor, "action": action, "hash": h}

    # --- writes --------------------------------------------------------------------------------
    def is_empty(self) -> bool:
        return bool(self._q("SELECT COUNT(*) FROM cases")[0][0] == 0)

    def add_case(self, case: dict[str, Any]) -> None:
        """Insert a routed case. Autonomous cases are executed immediately and logged as such."""
        auto = case["tier"] == "autonomous"
        with self._tx() as db:
            db.execute(
                "INSERT INTO cases (id, domain, seq, tier, status, priority, created_at, routing, "
                "features, explanation, ai_decision, final_decision, truth, decided_by, decided_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    case["id"], case["domain"], case["seq"], case["tier"],
                    "auto_executed" if auto else "pending", case["priority"], _now(),
                    json.dumps(case["routing"]), json.dumps(case["features"]),
                    json.dumps(case["explanation"]), case["ai_decision"],
                    case["ai_decision"] if auto else None, case["truth"],
                    "system:autonomous" if auto else None, _now() if auto else None,
                ),
            )  # fmt: skip
            self._append(db, case["id"], "system:router", "routed", case["routing"])
            if auto:
                self._append(
                    db, case["id"], "system:autonomous", "executed",
                    {"final_decision": case["ai_decision"]},
                )  # fmt: skip

    def decide(self, case_id: str, actor: str, action: str, reason: str | None) -> dict[str, Any]:
        """Record a reviewer decision. Raises KeyError (unknown case) or ValueError (not pending,
        or an action that the case's tier does not allow)."""
        with self._tx() as db:
            row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
            if row is None:
                raise KeyError(case_id)
            if row["status"] != "pending":
                raise ValueError(f"case is {row['status']}, not pending")
            allowed = {"review": {"accept", "override"}, "approval": {"approve", "override"}}
            if action not in allowed.get(row["tier"], set()):
                raise ValueError(f"action '{action}' is not allowed for a {row['tier']} case")
            if row["tier"] == "approval" and len((reason or "").strip()) < 10:
                raise ValueError(
                    "a mandatory approval needs a justification of at least 10 characters"
                )
            routing = json.loads(row["routing"])
            ai = row["ai_decision"]
            final = ai
            if action == "override":
                pos, neg = routing["positive_action"], routing["negative_action"]
                final = neg if ai == pos else pos
            ts = _now()
            db.execute(
                "UPDATE cases SET status = 'decided', final_decision = ?, decided_by = ?, "
                "decided_at = ?, reason = ? WHERE id = ?",
                (final, actor, ts, reason, case_id),
            )
            event = self._append(
                db, case_id, actor, action,
                {"ai_decision": ai, "final_decision": final, "reason": reason, "tier": row["tier"]},
            )  # fmt: skip
        return {"final_decision": final, "event": event}

    # --- reads ---------------------------------------------------------------------------------
    def queue(
        self, domain: str | None, tier: str | None, status: str, limit: int
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM cases WHERE status = ?"
        args: list[Any] = [status]
        if domain:
            sql += " AND domain = ?"
            args.append(domain)
        if tier:
            sql += " AND tier = ?"
            args.append(tier)
        # Mandatory approvals first, then highest expected cost; decided cases newest first.
        if status == "pending":
            sql += " ORDER BY CASE tier WHEN 'approval' THEN 0 ELSE 1 END, priority DESC, seq"
        else:
            sql += " ORDER BY decided_at DESC, seq"
        sql += " LIMIT ?"
        args.append(limit)
        return [self._public(r) for r in self._q(sql, args)]

    def case(self, case_id: str) -> dict[str, Any] | None:
        rows = self._q("SELECT * FROM cases WHERE id = ?", (case_id,))
        if not rows:
            return None
        row = rows[0]
        out = self._public(row, detail=True)
        out["audit"] = self.audit(case_id=case_id, limit=100)
        return out

    def _public(self, row: sqlite3.Row, detail: bool = False) -> dict[str, Any]:
        routing = json.loads(row["routing"])
        out: dict[str, Any] = {
            "id": row["id"], "domain": row["domain"], "seq": row["seq"], "tier": row["tier"],
            "status": row["status"], "ai_decision": row["ai_decision"],
            "created_at": row["created_at"],
            "confidence": routing["confidence"], "stake": routing["stake"],
            "expected_cost": routing["expected_cost"], "rules_fired": routing["rules_fired"],
            "final_decision": row["final_decision"], "decided_by": row["decided_by"],
            "decided_at": row["decided_at"],
        }  # fmt: skip
        if detail:
            out["routing"] = routing
            out["features"] = json.loads(row["features"])
            out["explanation"] = json.loads(row["explanation"])
            out["reason"] = row["reason"]
        if row["status"] != "pending":
            # Revealed only once a decision exists, so reviewers never see the label first.
            out["truth"] = row["truth"]
            out["correct"] = row["final_decision"] == row["truth"]
        return out

    def audit(
        self, case_id: str | None = None, limit: int = 200, before: int | None = None
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM audit WHERE 1 = 1"
        args: list[Any] = []
        if case_id:
            sql += " AND case_id = ?"
            args.append(case_id)
        if before is not None:
            sql += " AND seq < ?"
            args.append(before)
        sql += " ORDER BY seq DESC LIMIT ?"
        args.append(limit)
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in self._q(sql, args)]

    def verify(self) -> dict[str, Any]:
        """Recompute the hash chain from the first event."""
        prev = GENESIS
        n = 0
        for r in self._q("SELECT * FROM audit ORDER BY seq"):
            expected = event_hash(
                prev, r["ts"], r["case_id"], r["actor"], r["action"], r["payload"]
            )
            if r["prev_hash"] != prev or r["hash"] != expected:
                return {"valid": False, "events": n, "first_bad_seq": r["seq"]}
            prev = r["hash"]
            n += 1
        return {"valid": True, "events": n, "head": prev}

    def stats(self) -> dict[str, Any]:
        counts: dict[str, dict[str, int]] = {}
        for r in self._q(
            "SELECT domain, status, tier, COUNT(*) AS n FROM cases GROUP BY domain, status, tier"
        ):
            counts.setdefault(r["domain"], {})
            key = f"{r['status']}:{r['tier']}"
            counts[r["domain"]][key] = r["n"]
        decided = self._q(
            "SELECT ai_decision, final_decision, truth FROM cases WHERE status = 'decided'"
        )
        overrides = [r for r in decided if r["final_decision"] != r["ai_decision"]]
        ai_wrong = [r for r in decided if r["ai_decision"] != r["truth"]]
        oldest = self._q("SELECT MIN(created_at) FROM cases WHERE status = 'pending'")[0][0]
        return {
            "counts": counts,
            "oldest_pending_at": oldest,
            "human_decisions": len(decided),
            "override_rate": len(overrides) / len(decided) if decided else None,
            "override_precision": (
                sum(r["final_decision"] == r["truth"] for r in overrides) / len(overrides)
                if overrides
                else None
            ),
            "accepted_wrong_ai": sum(
                1 for r in ai_wrong if r["final_decision"] == r["ai_decision"]
            ),
            "caught_wrong_ai": sum(1 for r in ai_wrong if r["final_decision"] != r["ai_decision"]),
            "human_accuracy": (
                sum(r["final_decision"] == r["truth"] for r in decided) / len(decided)
                if decided
                else None
            ),
        }
