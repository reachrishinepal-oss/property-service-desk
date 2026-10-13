"""
PURPOSE: Command line runner that scores model deployments on the triage evaluation set.
LAYER:   Evaluation/Reliability
SESSION: S01
Run:     python scripts/run_triage_eval.py --deployments ai103model1,ai103model2,ai103model3 [--limit N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.governance.triage_eval import (  # noqa: E402 - needs the repo root on sys.path
    format_summary,
    load_eval_set,
    run_eval,
    write_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--deployments",
        required=True,
        help="comma-separated deployment names, for example ai103model1,ai103model2",
    )
    parser.add_argument("--limit", type=int, default=None, help="only use the first N rows")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deployments = [name.strip() for name in args.deployments.split(",") if name.strip()]
    if not deployments:
        print("ERROR: --deployments needs at least one name")
        return 1
    rows = load_eval_set()
    if args.limit is not None:
        rows = rows[: args.limit]
    print(f"Scoring {len(rows)} rows on {len(deployments)} deployment(s): {', '.join(deployments)}\n")
    try:
        result = run_eval(rows, deployments)
    except NotImplementedError as exc:
        print(f"Next step: {exc}")
        return 0
    path = write_results(result["records"])
    print(format_summary(result["summary"]))
    print(f"\nResults: {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
