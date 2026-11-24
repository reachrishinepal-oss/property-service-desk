"""
PURPOSE: Send the 12 red-team prompts through the same path the chat uses and write what happened to docs/RED_TEAM_LOG.md.
LAYER:   Evaluation/Reliability, Security/Controls
SESSION: S04
Run:     python scripts/run_redteam.py --guardrail contoso-strict
         (--guardrail is only a label for the log; the guardrail itself is assigned to the deployment in the portal)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.foundry import direct_openai_client  # noqa: E402
from src.governance.filter_outcomes import FilterStop  # noqa: E402
from src.tools.work_order_tools import reply_with_tools  # noqa: E402

REDTEAM_FILE = REPO_ROOT / "data" / "redteam" / "redteam_v1.jsonl"
POISONED_FILE = REPO_ROOT / "data" / "redteam" / "poisoned_rules.md"
LOG_FILE = REPO_ROOT / "docs" / "RED_TEAM_LOG.md"
INDIRECT_ID = "R12"  # asked with file_search against a temporary store holding the poisoned rules page


def create_poisoned_store() -> str:
    """Create a temporary vector store holding only the poisoned rules page, and return its id."""
    client = direct_openai_client()
    store = client.vector_stores.create(name="contoso-redteam-poisoned")
    with POISONED_FILE.open("rb") as handle:
        client.vector_stores.file_batches.upload_and_poll(vector_store_id=store.id, files=[handle])
    return store.id


def delete_store(store_id: str) -> None:
    """Delete the temporary store and the file uploaded into it."""
    client = direct_openai_client()
    file_ids = [item.id for item in client.vector_stores.files.list(vector_store_id=store_id)]
    client.vector_stores.delete(store_id)
    for file_id in file_ids:
        client.files.delete(file_id)


def attack(text: str, vector_store_id: str | None = None) -> tuple[str, str]:
    """Send one red-team prompt through the chat path; return (output, route)."""
    # AI-103 1.4.b: red team testing: deliberately attack your own assistant through the real chat path and write down what happened.
    try:
        reply, tool_log, searches, _ = reply_with_tools([{"role": "user", "content": text}], vector_store_id=vector_store_id)
    except FilterStop as stop:
        if stop.kind == "prompt_blocked":
            return "BLOCKED HTTP 400", "prompt blocked by the guardrail (content_filter); app shows the fallback"
        return stop.message, f"{stop.kind}; app shows this message"
    tools = ", ".join(call["name"] for call in tool_log)
    route = "reply" + (f" after tool calls: {tools}" if tools else "") + (" with rules search" if searches else "")
    if vector_store_id:
        route += " (poisoned store)"
    return reply[:300], route


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the red-team set through the chat path and log the results.")
    parser.add_argument("--guardrail", required=True, help="the guardrail assigned to the deployment, recorded in the log only")
    args = parser.parse_args()
    rows = [json.loads(line) for line in REDTEAM_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    lines = [
        "# Red team log",
        "",
        "Each prompt in `data/redteam/redteam_v1.jsonl` sent once through the chat path (Responses API, `ai103model1`, "
        f"`scripts/run_redteam.py`). {INDIRECT_ID} used a temporary vector store holding only `data/redteam/poisoned_rules.md`, "
        "deleted after the run. Output is the first 300 characters. One run, so wording can vary between runs.",
        "",
        "| Date | Id | Kind | Input | Output | Route | Guardrail | Meets expected? (Rishi) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        print(f"{row['id']} {row['kind']} ...", flush=True)
        if row["id"] == INDIRECT_ID:
            store_id = create_poisoned_store()
            try:
                output, route = attack(row["text"], vector_store_id=store_id)
            finally:
                delete_store(store_id)
        else:
            output, route = attack(row["text"])
        lines.append(f"| {date.today()} | {row['id']} | {row['kind']} | {cell(row['text'])} | {cell(output)} | "
                     f"{cell(route)} | {args.guardrail} | |")
    LOG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {LOG_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
