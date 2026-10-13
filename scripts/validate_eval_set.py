"""
PURPOSE: Check the triage evaluation set for schema and label errors and print its label mix.
LAYER:   Evaluation/Reliability
SESSION: S01
Run:     python scripts/validate_eval_set.py [path]   (default: data/eval/triage_eval_v1.jsonl)

Standard library only. Exits with code 1 on any error.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO_ROOT / "data" / "eval" / "triage_eval_v1.jsonl"
EXPECTED_ROWS = 20

CATEGORIES = {
    "plumbing", "electrical", "hvac", "appliance", "pest",
    "noise", "access_security", "common_area", "lease_billing",
}
URGENCIES = {"emergency", "urgent", "routine"}
LANGUAGES = {"en", "ar", "mixed"}
FIELDS = {
    "id": str,
    "text": str,
    "language": str,
    "expected_category": str,
    "expected_urgency": str,
    "hard": bool,
    "note": str,
}
ID_PATTERN = re.compile(r"^T\d{2}$")


def validate_row(row: object, line_no: int) -> list[str]:
    where = f"line {line_no}"
    if not isinstance(row, dict):
        return [f"{where}: expected a JSON object"]
    errors = []
    missing = FIELDS.keys() - row.keys()
    extra = row.keys() - FIELDS.keys()
    if missing:
        errors.append(f"{where}: missing fields {sorted(missing)}")
    if extra:
        errors.append(f"{where}: unexpected fields {sorted(extra)}")
    for name, kind in FIELDS.items():
        if name in row and type(row[name]) is not kind:
            errors.append(f"{where}: '{name}' must be {kind.__name__}")
    for name in ("text", "note"):
        if isinstance(row.get(name), str) and not row[name].strip():
            errors.append(f"{where}: '{name}' is empty")
    if isinstance(row.get("id"), str) and not ID_PATTERN.match(row["id"]):
        errors.append(f"{where}: id '{row['id']}' must look like T01")
    allowed = (
        ("language", LANGUAGES),
        ("expected_category", CATEGORIES),
        ("expected_urgency", URGENCIES),
    )
    for name, values in allowed:
        if isinstance(row.get(name), str) and row[name] not in values:
            errors.append(f"{where}: '{name}' value '{row[name]}' not in {sorted(values)}")
    return errors


def print_counts(title: str, counts: Counter) -> None:
    print(f"\n{title}")
    for key, count in sorted(counts.items(), key=lambda item: (-item[1], str(item[0]))):
        print(f"  {str(key):<16} {count}")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    if not path.is_file():
        print(f"ERROR: file not found: {path}")
        return 1

    errors: list[str] = []
    rows: list[dict] = []
    ids: Counter = Counter()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            errors.append(f"line {line_no}: blank line")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON ({exc.msg})")
            continue
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            ids[row["id"]] += 1
        row_errors = validate_row(row, line_no)
        errors.extend(row_errors)
        if not row_errors:
            rows.append(row)

    for row_id, count in sorted(ids.items()):
        if count > 1:
            errors.append(f"id '{row_id}' appears {count} times")
    if len(rows) != EXPECTED_ROWS:
        errors.append(f"expected exactly {EXPECTED_ROWS} valid rows, found {len(rows)}")

    print(f"File: {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")
    print(f"Valid rows: {len(rows)}")
    print_counts("Category", Counter(row["expected_category"] for row in rows))
    print_counts("Urgency", Counter(row["expected_urgency"] for row in rows))
    print_counts("Language", Counter(row["language"] for row in rows))
    print_counts("Hard", Counter(row["hard"] for row in rows))

    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("\nOK: schema, values, ids and row count all valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
