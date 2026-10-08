"""Command-line interface: ``governance run|report|serve|route``."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="governance", description=__doc__)
    parser.add_argument(
        "--root", default=os.environ.get("GOVERNANCE_ROOT", "."), help="project root"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run an experiment config (writes results/<experiment>/<run>/)")
    r.add_argument("config")
    r.add_argument("--quiet", action="store_true")

    sub.add_parser("report", help="regenerate research/generated tables and figures")

    s = sub.add_parser("serve", help="serve the decision console and API")
    s.add_argument("--host", default=os.environ.get("GOVERNANCE_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("GOVERNANCE_PORT", "8000")))

    q = sub.add_parser(
        "route", help="route one seed's test stream under a policy and print tier shares"
    )
    q.add_argument("policy")
    q.add_argument("--seed", type=int, default=0)

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "run":
        from governance.experiments.runner import run_experiment

        out = run_experiment(Path(args.config), root, quiet=args.quiet)
        print(out.relative_to(root))
        return 0
    if args.cmd == "report":
        from governance.experiments.report import generate_report

        for p in generate_report(root):
            print(p.relative_to(root))
        return 0
    if args.cmd == "serve":
        import uvicorn

        from governance.api.app import create_app

        uvicorn.run(create_app(root), host=args.host, port=args.port, log_level="info")
        return 0
    if args.cmd == "route":
        import numpy as np

        from governance.experiments.stream import build_stream
        from governance.humans.reviewer import ReviewerModel, Staffing
        from governance.policy.policy import TIERS, Policy, route

        policy = Policy.load(Path(args.policy))
        st = build_stream(policy.domain, args.seed, ReviewerModel(), Staffing())
        routing = route(policy, st.ctx.domain, st.ctx.out)
        shares = {t: round(float(np.mean(routing.tier == i)), 4) for i, t in enumerate(TIERS)}
        print(
            json.dumps({"policy": policy.id, "hash": policy.hash, "tier_share": shares}, indent=1)
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
