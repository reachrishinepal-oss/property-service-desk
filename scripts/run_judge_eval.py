"""
PURPOSE: Command line runner that generates service desk replies and has a judge model score them.
LAYER:   Evaluation/Reliability
SESSION: S01
Run:     python scripts/run_judge_eval.py [--limit N] [--replies-file PATH [--ids T06,T10] [--merge-into JUDGE_JSON]]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.governance.judge_eval import (  # noqa: E402 - needs the repo root on sys.path
    EvalNotValid,
    generate_replies,
    load_eval_requests,
    merge_judge_results,
    read_replies,
    run_judges,
    screen_replies,
    summarise,
    write_judge_results,
    write_replies,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--limit", type=int, default=None, help="only use the first N rows")
    parser.add_argument(
        "--replies-file",
        type=Path,
        default=None,
        help="judge an existing replies_*.jsonl file instead of generating new replies",
    )
    parser.add_argument("--ids", default=None, help="with --replies-file: only judge these row ids, comma separated")
    parser.add_argument(
        "--merge-into",
        type=Path,
        default=None,
        help="an earlier judge_*.json; the new scores replace its rows of the same id and the averages are recomputed",
    )
    return parser.parse_args()


def _show(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def main() -> int:
    args = parse_args()
    try:
        if args.replies_file is not None:
            replies_path = args.replies_file
            if not replies_path.is_file():
                print(f"ERROR: replies file not found: {replies_path}")
                return 1
            if args.limit is not None:
                print("Note: --limit is ignored when --replies-file is given.")
            print(f"Judging existing replies: {_show(replies_path)}\n")
        else:
            rows = load_eval_requests()
            if args.limit is not None:
                rows = rows[: args.limit]
            print(f"Generating replies for {len(rows)} rows ...")
            records = generate_replies(rows)
            errors = [r for r in records if r["error"]]
            replies_path = write_replies(records)
            print(f"Replies: {_show(replies_path)} ({len(errors)} error(s))")
            for record in errors:
                print(f"  {record['id']}  {record['error']}")
            print()
        records = read_replies(replies_path)
        if args.ids:
            wanted = {i.strip() for i in args.ids.split(",")}
            records = [r for r in records if r.get("id") in wanted]
            print(f"Only judging rows: {', '.join(r['id'] for r in records)}")
        kept, messages = screen_replies(records)
        for message in messages:
            print(message)
        judged_path = write_replies(kept, prefix="judged")
        print(f"Judge input: {_show(judged_path)}\n")
        result = run_judges(judged_path)
    except EvalNotValid as exc:
        print(f"STOPPED: {exc}")
        return 1
    except NotImplementedError as exc:
        print(f"Next step: {exc}")
        return 0
    if args.merge_into is not None:
        earlier = json.loads(args.merge_into.read_text(encoding="utf-8"))
        result = merge_judge_results(earlier, result)
        print(f"Merged into the rows of {_show(args.merge_into)}\n")
    for row in result["rows"]:
        if row.get("judge_error"):
            print(f"Still not scored: {row['id']}  {row['judge_error']}")
    path = write_judge_results(result)
    print(summarise(result))
    print(f"\nJudge results: {_show(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
