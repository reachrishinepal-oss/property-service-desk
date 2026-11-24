"""
PURPOSE: Command line runner that scores model deployments on the triage evaluation set.
LAYER:   Evaluation/Reliability
SESSION: S01 (--prompt and --eval-file added in S04)
Run:     python scripts/run_triage_eval.py --deployments ai103model1,ai103model2,ai103model3 [--limit N]
         python scripts/run_triage_eval.py --deployments ai103model1 --prompt v2 --eval-file data/eval/triage_eval_v2.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.governance.triage_eval import (  # noqa: E402 - needs the repo root on sys.path
    DEFAULT_EVAL_PATH,
    classifier_for,
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
    parser.add_argument("--prompt", choices=["v1", "v2"], default="v1", help="triage prompt to use (default v1)")
    parser.add_argument("--eval-file", default=str(DEFAULT_EVAL_PATH), help="JSONL eval set (default triage_eval_v1.jsonl)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deployments = [name.strip() for name in args.deployments.split(",") if name.strip()]
    if not deployments:
        print("ERROR: --deployments needs at least one name")
        return 1
    eval_file = Path(args.eval_file)
    rows = load_eval_set(eval_file)
    if args.limit is not None:
        rows = rows[: args.limit]
    print(f"Scoring {len(rows)} rows of {eval_file.name} with prompt {args.prompt} "
          f"on {len(deployments)} deployment(s): {', '.join(deployments)}\n")
    try:
        result = run_eval(rows, deployments, classify=classifier_for(args.prompt))
    except NotImplementedError as exc:
        print(f"Next step: {exc}")
        return 0
    path = write_results(result["records"], tag=f"{args.prompt}_{eval_file.stem}")
    print(format_summary(result["summary"]))
    print(f"\nResults: {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
