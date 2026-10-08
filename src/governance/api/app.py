"""Decision-console API: experiment results (read-only), policies, and the live review queue.

Security posture
- Reads are open on localhost; ``GOVERNANCE_API_TOKEN`` (optional) protects every ``/api`` route
  except ``/api/health`` when the server is exposed.
- Writes (reviewer decisions) need a reviewer token from ``GOVERNANCE_REVIEWER_TOKENS``
  (``name:token`` pairs, comma separated), sent in the ``X-Reviewer-Token`` header. The
  reviewer identity in the audit log comes from the token, never from the request body. If no
  reviewer tokens are configured, writes are disabled.
- Every client is rate limited (token bucket); writes have a stricter bucket.
- Path segments are validated against allow-lists; there is no file access by user-supplied path.
- Security headers (CSP without inline scripts, nosniff, no-referrer, frame-ancestors 'none').
"""

from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, model_validator
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from governance.api.store import Store
from governance.data.domains import DOMAINS
from governance.experiments.report import DOMAIN_LABELS, EXPERIMENTS, ROUTER_LABELS
from governance.policy.policy import TIERS, Policy
from governance.regimes.regimes import REGIME_LABELS, REGIMES

_SAFE = re.compile(r"^[A-Za-z0-9_.\-]{1,120}$")


class RateLimiter:
    def __init__(self, rate: float, burst: int) -> None:
        self.rate, self.burst = rate, burst
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (float(self.burst), now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens < 1:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1, now)
            return True


def parse_reviewer_tokens(raw: str | None) -> dict[str, str]:
    """``"alice:tok1,bob:tok2"`` -> {token: name}. Malformed entries are rejected loudly."""
    out: dict[str, str] = {}
    for item in (raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, sep, token = item.partition(":")
        if not sep or not re.fullmatch(r"[a-z0-9_-]{1,32}", name) or len(token) < 16:
            raise ValueError(
                "GOVERNANCE_REVIEWER_TOKENS must be name:token pairs "
                "(name: lowercase letters, digits, _ or -; token: at least 16 characters)"
            )
        out[token] = name
    return out


class GuardMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app: Any, read_token: str | None, reads: RateLimiter, writes: RateLimiter
    ) -> None:
        super().__init__(app)
        self.read_token, self.reads, self.writes = read_token, reads, writes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith("/api"):
            client = request.client.host if request.client else "unknown"
            limiter = self.writes if request.method in {"POST", "PUT", "DELETE"} else self.reads
            if not limiter.allow(client):
                return JSONResponse(
                    {"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "1"}
                )
            if self.read_token and request.method == "GET" and request.url.path != "/api/health":
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied.encode(), self.read_token.encode()):
                    return JSONResponse({"detail": "unauthorized"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        return response


class DecisionIn(BaseModel):
    action: Literal["accept", "approve", "override"]
    reason: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def reason_for_override(self) -> DecisionIn:
        if self.action == "override" and len((self.reason or "").strip()) < 10:
            raise ValueError("an override needs a reason of at least 10 characters")
        return self


def _safe(segment: str) -> str:
    if not _SAFE.match(segment) or segment in {".", ".."}:
        raise HTTPException(400, "invalid identifier")
    return segment


def create_app(
    root: Path,
    db_path: Path | None = None,
    static_dir: Path | None = None,
    seed_domains: tuple[str, ...] = DOMAINS,
    seed_cases: int | None = None,
) -> FastAPI:
    root = root.resolve()
    results = root / "results"
    static = static_dir or root / "web" / "dist"
    db = db_path or Path(os.environ.get("GOVERNANCE_DB", root / "var" / "governance.db"))
    reviewers = parse_reviewer_tokens(os.environ.get("GOVERNANCE_REVIEWER_TOKENS"))
    n_cases = (
        seed_cases
        if seed_cases is not None
        else int(os.environ.get("GOVERNANCE_SEED_CASES", "200"))
    )
    store = Store(db)
    if store.is_empty() and n_cases > 0:
        from governance.api.seed import seed_queue

        seed_queue(store, root, seed_domains, seed=0, n_cases=n_cases)

    app = FastAPI(
        title="Decision governance console API",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        GuardMiddleware,
        read_token=os.environ.get("GOVERNANCE_API_TOKEN") or None,
        reads=RateLimiter(rate=float(os.environ.get("GOVERNANCE_RATE_PER_SEC", "50")), burst=200),
        writes=RateLimiter(rate=1.0, burst=20),
    )
    app.state.store = store

    def reviewer_for(request: Request) -> str:
        if not reviewers:
            raise HTTPException(403, "reviewer writes are disabled (no GOVERNANCE_REVIEWER_TOKENS)")
        supplied = request.headers.get("x-reviewer-token", "").strip()
        for token, name in reviewers.items():
            if hmac.compare_digest(supplied.encode(), token.encode()):
                return f"reviewer:{name}"
        raise HTTPException(401, "invalid reviewer token")

    def summary_of(exp: str) -> dict[str, Any]:
        if exp not in EXPERIMENTS:
            raise HTTPException(404, f"unknown experiment '{exp}'")
        marker = results / exp / "LATEST"
        if not marker.exists():
            raise HTTPException(404, "experiment has no completed run")
        run = _safe(marker.read_text().strip())
        data: dict[str, Any] = json.loads((results / exp / run / "summary.json").read_text())
        return data

    # --- meta and results ----------------------------------------------------------------------
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "writes_enabled": bool(reviewers)}

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        return {
            "domains": [{"id": d, "label": DOMAIN_LABELS[d]} for d in DOMAINS],
            "tiers": list(TIERS),
            "regimes": [{"id": r, "label": REGIME_LABELS[r]} for r in REGIMES],
            "routers": ROUTER_LABELS,
            "writes_enabled": bool(reviewers),
        }

    @app.get("/api/reviewer")
    def reviewer(request: Request) -> dict[str, Any]:
        """Checks a reviewer token (the console's sign-in) without changing anything."""
        return {"reviewer": reviewer_for(request)}

    @app.get("/api/experiments")
    def experiments() -> list[dict[str, Any]]:
        out = []
        for exp in EXPERIMENTS:
            marker = results / exp / "LATEST"
            if not marker.exists():
                out.append({"experiment": exp, "status": "pending"})
                continue
            prov = summary_of(exp)["provenance"]
            out.append({"experiment": exp, "status": "complete", **prov})
        return out

    @app.get("/api/experiments/{exp}")
    def experiment(exp: str) -> dict[str, Any]:
        return summary_of(_safe(exp))

    @app.get("/api/policies")
    def policies() -> list[dict[str, Any]]:
        out = []
        for d in DOMAINS:
            p = Policy.load(root / "configs" / "policies" / f"{d}.yaml")
            out.append({**p.model_dump(), "hash": p.hash, "path": f"configs/policies/{d}.yaml"})
        return out

    # --- review queue --------------------------------------------------------------------------
    @app.get("/api/queue")
    def queue(
        domain: str | None = Query(None, pattern=r"^(credit|eligibility|payments)$"),
        tier: str | None = Query(None, pattern=r"^(autonomous|review|approval)$"),
        status: str = Query("pending", pattern=r"^(pending|decided|auto_executed)$"),
        limit: int = Query(100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        return store.queue(domain, tier, status, limit)

    @app.get("/api/cases/{case_id}")
    def case(case_id: str) -> dict[str, Any]:
        c = store.case(_safe(case_id))
        if c is None:
            raise HTTPException(404, "unknown case")
        return c

    @app.post("/api/cases/{case_id}/decision")
    def decide(case_id: str, body: DecisionIn, request: Request) -> dict[str, Any]:
        actor = reviewer_for(request)
        try:
            store.decide(_safe(case_id), actor, body.action, (body.reason or "").strip() or None)
        except KeyError as exc:
            raise HTTPException(404, "unknown case") from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        c = store.case(case_id)
        assert c is not None
        return c

    @app.get("/api/stats")
    def stats() -> dict[str, Any]:
        return store.stats()

    @app.get("/api/audit")
    def audit(
        case_id: str | None = Query(None, max_length=120),
        limit: int = Query(100, ge=1, le=500),
        before: int | None = Query(None, ge=1),
    ) -> list[dict[str, Any]]:
        return store.audit(_safe(case_id) if case_id else None, limit, before)

    @app.get("/api/audit/verify")
    def verify() -> dict[str, Any]:
        return store.verify()

    # --- static console ------------------------------------------------------------------------
    if static.is_dir():
        index = static / "index.html"

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404)
            target = (static / path).resolve()
            if path and target.is_file() and target.is_relative_to(static.resolve()):
                return FileResponse(target)
            return FileResponse(index)

    return app
