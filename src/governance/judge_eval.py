"""
PURPOSE: Generate service desk replies for the eval set, have a judge model score them, and save and summarise the scores.
LAYER:   Evaluation/Reliability
SESSION: S01
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from src.intelligence.hello import first_reply

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVAL_PATH = REPO_ROOT / "data" / "eval" / "triage_eval_v1.jsonl"
DEFAULT_RESULTS_DIR = REPO_ROOT / "data" / "eval" / "results"

# Metric names as the azure-ai-evaluation evaluators report them, scored 1 to 5.
EVALUATORS = ("relevance", "coherence", "fluency")
GOOD_SCORE = 4
REASON_CHARS = 90

# Share of failed replies (0 to 1). Strictly above WARN_ABOVE prints a warning;
# strictly above STOP_ABOVE the run stops because the scores would not be valid.
WARN_ABOVE = 0.10
STOP_ABOVE = 0.20

Reply = Callable[[str], str]


def load_eval_requests(path: str | Path = DEFAULT_EVAL_PATH) -> list[dict]:
    """Read the eval set and keep only id and text; expected labels are not needed here."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows.append({"id": row["id"], "text": row["text"]})
    return rows


def generate_replies(rows: list[dict], reply: Reply = first_reply) -> list[dict]:
    """Ask the service desk for a reply to every row. A failed row keeps an "error" and an empty response."""
    records = []
    for row in rows:
        record = {"id": row["id"], "query": row["text"], "response": "", "error": None}
        try:
            record["response"] = reply(row["text"])
        except NotImplementedError:
            # An unfinished feature is not a model error: stop the whole run.
            raise
        except Exception as exc:  # noqa: BLE001 - one bad row must not stop the run
            record["error"] = f"{type(exc).__name__}: {exc}"
        records.append(record)
    return records


def write_replies(
    records: list[dict], results_dir: str | Path = DEFAULT_RESULTS_DIR, prefix: str = "replies"
) -> Path:
    """Write one JSON object per line to results_dir/<prefix>_YYYYMMDD_HHMMSS.jsonl, always with query and response."""
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            line = {**record, "query": record.get("query", ""), "response": record.get("response") or ""}
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    return path


def read_replies(path: str | Path) -> list[dict]:
    """Read a replies JSONL file back into records."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class EvalNotValid(Exception):
    """Too many replies failed to generate for the judge scores to mean anything."""


def _failed(record: dict) -> bool:
    return bool(record.get("error")) or not str(record.get("response") or "").strip()


def screen_replies(
    records: list[dict], warn_above: float = WARN_ABOVE, stop_above: float = STOP_ABOVE
) -> tuple[list[dict], list[str]]:
    """Leave out failed replies before judging. Return (kept records, messages to print).

    A reply failed if it has an error or an empty response. Raises EvalNotValid when
    there are no replies or the failed share is strictly above stop_above.
    """
    total = len(records)
    if total == 0:
        raise EvalNotValid("Evaluation is not valid: there are no replies to judge.")
    kept = [r for r in records if not _failed(r)]
    failed = total - len(kept)
    share = failed / total
    messages = [f"{failed} of {total} replies failed and were not judged."]
    if share > stop_above:
        raise EvalNotValid(
            f"{messages[0]} Evaluation is not valid: {share:.0%} failed, above the {stop_above:.0%} limit. "
            "Fix the failures and run again."
        )
    if share > warn_above:
        messages.append(
            f"WARNING: {share:.0%} of replies failed, above {warn_above:.0%}. "
            "Scores cover only the replies that worked; treat them with care."
        )
    return kept, messages


def run_judges(replies_path: str | Path) -> dict:
    """Score every reply in replies_path with the Relevance, Coherence and Fluency judges."""
    # AI-103 2.1.d, 1.4.b: a judge model (AI-assisted evaluators) scores each reply for relevance, coherence and fluency, with a written reason.
    # Steps:    1. Read the replies file: one line per reply, with the resident's message and the model's reply.
    #          2. Set up the judge model, deployment ai103model3, with keyless sign-in if the package allows it.
    #          3. For each reply, have the judge assess relevance, then coherence, then fluency (fluency matters most on Arabic replies).
    #          4. Keep each score together with the judge's written reason, row by row.
    #          5. Work out the average for each of the three checks, with no combined score, and return the rows and the averages.
    #          6. If a row cannot be scored, record None for it and carry on.
    # Decision: Judge is ai103model3 (gpt-5). Replies come from the CHAT_DEPLOYMENT in .env, ai103model1 (gpt-4.1-mini),
    #          so the judge does not grade its own work.
    #          Reason: I want a capability gap between the judge and gpt-4.1-mini so similar models do not favour each other (response bias),
    #          and gpt-5 is a reasoning model built for multi-step reasoning, which scoring against a rubric needs, while gpt-4.1-mini is tuned for fast chat.
    #          Limits: same lab and family as the reply model (self-preference bias possible), slower, and costlier per token.
    #          gpt-5 is a reasoning model, so the evaluators run in reasoning-model mode. Keyless sign-in.
    # Predict:  About 4.5 out of 5 on relevance, coherence and fluency from gpt-4.1-mini replies judged by gpt-5;
    #          fluency possibly lower on the Arabic replies.
    from azure.ai.evaluation import CoherenceEvaluator, FluencyEvaluator, RelevanceEvaluator
    from azure.identity import DefaultAzureCredential

    from src.core.config import get_judge_endpoint

    # 1. Read the replies file.
    records = read_replies(replies_path)

    # 2. Set up the judge model, deployment ai103model3, with keyless sign-in.
    #    is_reasoning_model=True makes the evaluators send max_completion_tokens, which gpt-5 needs, instead of max_tokens.
    model_config = {"azure_endpoint": get_judge_endpoint(), "azure_deployment": "ai103model3"}
    credential = DefaultAzureCredential()
    relevance_judge = RelevanceEvaluator(model_config, credential=credential, is_reasoning_model=True)
    coherence_judge = CoherenceEvaluator(model_config, credential=credential, is_reasoning_model=True)
    fluency_judge = FluencyEvaluator(model_config, credential=credential, is_reasoning_model=True)

    rows = []
    for record in records:
        row = {"id": record.get("id"), "query": record["query"], "response": record["response"]}
        try:
            # 3. Relevance, then coherence, then fluency.
            relevance = relevance_judge(query=record["query"], response=record["response"])
            coherence = coherence_judge(query=record["query"], response=record["response"])
            fluency = fluency_judge(response=record["response"])
            # 4. Keep each score with the judge's reason.
            row["relevance"] = relevance["relevance"]
            row["relevance_reason"] = relevance["relevance_reason"]
            row["coherence"] = coherence["coherence"]
            row["coherence_reason"] = coherence["coherence_reason"]
            row["fluency"] = fluency["fluency"]
            row["fluency_reason"] = fluency["fluency_reason"]
        except Exception as exc:  # noqa: BLE001
            # 6. The row cannot be scored: record None and carry on.
            for name in EVALUATORS:
                row[name] = None
                row[f"{name}_reason"] = None
            row["judge_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)

    # 5. Average each check on its own, no combined score.
    return {"rows": rows, "metrics": average_scores(rows)}


def average_scores(rows: list[dict]) -> dict:
    """Average each evaluator over the rows the judge scored, leaving out None."""
    metrics = {}
    for name in EVALUATORS:
        scores = [row[name] for row in rows if row.get(name) is not None]
        metrics[name] = sum(scores) / len(scores) if scores else None
    return metrics


def merge_judge_results(earlier: dict, rescored: dict) -> dict:
    """Replace earlier rows with the re-scored rows of the same id, keep row order, and recompute the averages."""
    by_id = {row["id"]: row for row in rescored["rows"]}
    rows = [by_id.get(row["id"], row) for row in earlier["rows"]]
    return {"rows": rows, "metrics": average_scores(rows)}


def _shorten(text: str, limit: int = REASON_CHARS) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def summarise(result: dict) -> str:
    """Render one line per evaluator (average, rows scoring 4 or 5) and the reasons of its three lowest rows."""
    rows = result.get("rows", [])
    metrics = result.get("metrics", {})
    header = f"{'evaluator':<10} {'avg':>5} {'4-5/5':>7} {'scored':>6}"
    lines = [header, "-" * len(header)]
    lowest_blocks = []
    for name in EVALUATORS:
        scored = [r for r in rows if isinstance(r.get(name), (int, float))]
        average = metrics.get(name)
        if average is None and scored:
            average = sum(r[name] for r in scored) / len(scored)
        avg_text = "n/a" if average is None else f"{average:.2f}"
        good = sum(1 for r in scored if r[name] >= GOOD_SCORE)
        lines.append(f"{name:<10} {avg_text:>5} {f'{good}/{len(scored)}':>7} {len(scored):>6}")
        lowest = sorted(scored, key=lambda r: r[name])[:3]
        if lowest:
            block = [f"\nLowest {name}:"]
            for r in lowest:
                reason = _shorten(r.get(f"{name}_reason") or "(no reason given)")
                block.append(f"  {r.get('id', '?'):<5} {r[name]:>3g}  {reason}")
            lowest_blocks.extend(block)
    lines.append("avg = mean score out of 5; 4-5/5 = rows scoring 4 or 5 out of the rows the judge scored.")
    return "\n".join(lines + lowest_blocks)


def write_judge_results(result: dict, results_dir: str | Path = DEFAULT_RESULTS_DIR) -> Path:
    """Write the full judge result to results_dir/judge_YYYYMMDD_HHMMSS.json."""
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"judge_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    return path
