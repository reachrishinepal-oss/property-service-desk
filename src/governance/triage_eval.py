"""
PURPOSE: Run the triage evaluation set against model deployments, score the answers and save the results.
LAYER:   Evaluation/Reliability
SESSION: S01
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.intelligence.triage import classify_request

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_PATH = REPO_ROOT / "data" / "eval" / "triage_eval_v1.jsonl"
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"

Classify = Callable[[str, str], dict]


def load_eval_set(path: str | Path = DEFAULT_EVAL_PATH) -> list[dict]:
    """Read a JSONL eval set into a list of row dicts, skipping blank lines."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _ratio(hits: int, total: int) -> float | None:
    return hits / total if total else None


def _score_row(deployment: str, row: dict, classify: Classify) -> dict:
    """Call classify on the row text only, time it and compare with the expected labels."""
    record = {
        "id": row["id"],
        "deployment": deployment,
        "expected_category": row["expected_category"],
        "expected_urgency": row["expected_urgency"],
        "predicted_category": None,
        "predicted_urgency": None,
        "category_correct": False,
        "urgency_correct": False,
        "both_correct": False,
        "hard": row["hard"],
        "latency_s": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "error": None,
    }
    start = time.perf_counter()
    try:
        result = classify(deployment, row["text"])
        record["latency_s"] = round(time.perf_counter() - start, 3)
        record["predicted_category"] = result["category"]
        record["predicted_urgency"] = result["urgency"]
        for key in ("input_tokens", "output_tokens", "reasoning_tokens"):
            record[key] = int(result.get(key) or 0)
    except NotImplementedError:
        # An unfinished feature is not a model error: stop the whole run.
        raise
    except Exception as exc:  # noqa: BLE001 - one bad row must not stop the run
        record["latency_s"] = round(time.perf_counter() - start, 3)
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record
    record["category_correct"] = record["predicted_category"] == record["expected_category"]
    record["urgency_correct"] = record["predicted_urgency"] == record["expected_urgency"]
    record["both_correct"] = record["category_correct"] and record["urgency_correct"]
    return record


def summarise(records: list[dict]) -> dict:
    """Aggregate scored records for one deployment. Errors count as wrong answers."""
    easy = [r for r in records if not r["hard"]]
    ok = [r for r in records if r["error"] is None]
    return {
        "rows": len(records),
        "category_accuracy": _ratio(sum(r["category_correct"] for r in records), len(records)),
        "urgency_accuracy": _ratio(sum(r["urgency_correct"] for r in records), len(records)),
        "both_accuracy": _ratio(sum(r["both_correct"] for r in records), len(records)),
        "both_accuracy_not_hard": _ratio(sum(r["both_correct"] for r in easy), len(easy)),
        # Latency of successful calls only, so fast failures do not flatter the mean.
        "mean_latency_s": _ratio(sum(r["latency_s"] for r in ok), len(ok)),
        "input_tokens": sum(r["input_tokens"] for r in records),
        "output_tokens": sum(r["output_tokens"] for r in records),
        "reasoning_tokens": sum(r["reasoning_tokens"] for r in records),
        "errors": len(records) - len(ok),
        "misses": [
            {
                "id": r["id"],
                "expected": {"category": r["expected_category"], "urgency": r["expected_urgency"]},
                "predicted": {"category": r["predicted_category"], "urgency": r["predicted_urgency"]},
                "error": r["error"],
            }
            for r in records
            if not r["both_correct"]
        ],
    }


def run_eval(
    rows: list[dict],
    deployments: list[str],
    classify: Classify = classify_request,
) -> dict:
    """Score every (deployment, row) pair.

    classify receives ONLY (deployment, row["text"]); expected labels and the note
    never leave this module. Returns {"records": [...], "summary": {deployment: {...}}}.
    """
    records = []
    summary = {}
    for deployment in deployments:
        scored = [_score_row(deployment, row, classify) for row in rows]
        records.extend(scored)
        summary[deployment] = summarise(scored)
    return {"records": records, "summary": summary}


def write_results(records: list[dict], results_dir: str | Path = DEFAULT_RESULTS_DIR) -> Path:
    """Write one JSONL line per (deployment, row) to results_dir/run_YYYYMMDD_HHMMSS.jsonl."""
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def format_summary(summary: dict) -> str:
    """Render the per-deployment summary and misses as a plain-text table."""
    header = (
        f"{'deployment':<20} {'cat':>5} {'urg':>5} {'both':>5} {'easy':>5} "
        f"{'lat_s':>6} {'in_tok':>7} {'out_tok':>7} {'rsn_tok':>7} {'errors':>6}"
    )
    lines = [header, "-" * len(header)]
    for deployment, s in summary.items():
        latency = "n/a" if s["mean_latency_s"] is None else f"{s['mean_latency_s']:.2f}"
        lines.append(
            f"{deployment:<20} {_pct(s['category_accuracy']):>5} {_pct(s['urgency_accuracy']):>5} "
            f"{_pct(s['both_accuracy']):>5} {_pct(s['both_accuracy_not_hard']):>5} {latency:>6} "
            f"{s['input_tokens']:>7} {s['output_tokens']:>7} {s['reasoning_tokens']:>7} {s['errors']:>6}"
        )
    lines.append("cat/urg/both = accuracy on all rows; easy = both correct on rows where hard is false.")
    for deployment, s in summary.items():
        if not s["misses"]:
            continue
        lines.append(f"\nMisses for {deployment} ({len(s['misses'])}):")
        for miss in s["misses"]:
            exp, got = miss["expected"], miss["predicted"]
            detail = miss["error"] or f"got {got['category']}/{got['urgency']}"
            lines.append(f"  {miss['id']}  expected {exp['category']}/{exp['urgency']}  {detail}")
    return "\n".join(lines)
