"""
PURPOSE: Prove the triage eval runner scores correctly and never shows expected labels to the model.
LAYER:   Evaluation/Reliability
SESSION: S01
Run:     python -m unittest   (from the capstone folder)
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.governance.triage_eval import load_eval_set, run_eval, write_results

ROWS = [
    {"id": "T01", "text": "Water through the ceiling", "language": "en",
     "expected_category": "plumbing", "expected_urgency": "emergency", "hard": False,
     "note": "active leak"},
    {"id": "T02", "text": "Gym treadmill is broken", "language": "en",
     "expected_category": "common_area", "expected_urgency": "routine", "hard": False,
     "note": "shared space"},
    {"id": "T03", "text": "AC is weak and makes a noise", "language": "en",
     "expected_category": "hvac", "expected_urgency": "urgent", "hard": True,
     "note": "ambiguous"},
]
BY_TEXT = {row["text"]: row for row in ROWS}
TOKENS = {"input_tokens": 10, "output_tokens": 3, "reasoning_tokens": 2}


def perfect(deployment: str, text: str) -> dict:
    row = BY_TEXT[text]
    return {"category": row["expected_category"], "urgency": row["expected_urgency"], **TOKENS}


def always_wrong(deployment: str, text: str) -> dict:
    return {"category": "pest", "urgency": "routine" if BY_TEXT[text]["expected_urgency"] != "routine"
            else "emergency", "input_tokens": 5, "output_tokens": 1}


def raises(deployment: str, text: str) -> dict:
    raise RuntimeError("endpoint unavailable")


class ScoringTests(unittest.TestCase):
    def test_perfect_classifier_scores_full_marks(self):
        s = run_eval(ROWS, ["m1"], perfect)["summary"]["m1"]
        self.assertEqual(s["category_accuracy"], 1.0)
        self.assertEqual(s["urgency_accuracy"], 1.0)
        self.assertEqual(s["both_accuracy"], 1.0)
        self.assertEqual(s["both_accuracy_not_hard"], 1.0)
        self.assertEqual(s["errors"], 0)
        self.assertEqual(s["misses"], [])
        self.assertEqual(
            (s["input_tokens"], s["output_tokens"], s["reasoning_tokens"]), (30, 9, 6)
        )
        self.assertIsNotNone(s["mean_latency_s"])

    def test_wrong_classifier_scores_zero_and_lists_every_miss(self):
        s = run_eval(ROWS, ["m1"], always_wrong)["summary"]["m1"]
        self.assertEqual(s["category_accuracy"], 0.0)
        self.assertEqual(s["urgency_accuracy"], 0.0)
        self.assertEqual(s["both_accuracy"], 0.0)
        self.assertEqual(s["both_accuracy_not_hard"], 0.0)
        self.assertEqual(s["reasoning_tokens"], 0)  # missing key counts as 0
        self.assertEqual([m["id"] for m in s["misses"]], ["T01", "T02", "T03"])
        self.assertEqual(s["misses"][0]["expected"], {"category": "plumbing", "urgency": "emergency"})
        self.assertEqual(s["misses"][0]["predicted"], {"category": "pest", "urgency": "routine"})

    def test_raising_classifier_records_errors_and_continues(self):
        result = run_eval(ROWS, ["m1", "m2"], raises)
        self.assertEqual(len(result["records"]), 6)
        for deployment in ("m1", "m2"):
            s = result["summary"][deployment]
            self.assertEqual(s["errors"], 3)
            self.assertEqual(s["both_accuracy"], 0.0)
            self.assertIsNone(s["mean_latency_s"])
        self.assertTrue(all("endpoint unavailable" in r["error"] for r in result["records"]))

    def test_partial_scores_and_hard_rows_excluded_from_easy_accuracy(self):
        def right_except_hard(deployment, text):
            row = BY_TEXT[text]
            category = "noise" if row["hard"] else row["expected_category"]
            return {"category": category, "urgency": row["expected_urgency"]}

        s = run_eval(ROWS, ["m1"], right_except_hard)["summary"]["m1"]
        self.assertAlmostEqual(s["category_accuracy"], 2 / 3)
        self.assertEqual(s["urgency_accuracy"], 1.0)
        self.assertAlmostEqual(s["both_accuracy"], 2 / 3)
        self.assertEqual(s["both_accuracy_not_hard"], 1.0)

    def test_not_implemented_stops_the_run(self):
        def unfinished(deployment, text):
            raise NotImplementedError("LZ-01.1")

        with self.assertRaises(NotImplementedError):
            run_eval(ROWS, ["m1"], unfinished)


class LeakageTests(unittest.TestCase):
    def test_classify_only_receives_deployment_and_text(self):
        calls = []

        def spy(*args, **kwargs):
            calls.append((args, kwargs))
            return {"category": "pest", "urgency": "routine"}

        run_eval(ROWS, ["m1", "m2"], spy)
        self.assertEqual(len(calls), 6)
        expected_calls = [((d, row["text"]), {}) for d in ("m1", "m2") for row in ROWS]
        self.assertEqual(calls, expected_calls)
        hidden = {
            value for row in ROWS
            for value in (row["expected_category"], row["expected_urgency"], row["note"])
        }
        for args, _ in calls:
            for arg in args:
                self.assertIsInstance(arg, str)
                self.assertNotIn(arg, hidden)


class FileTests(unittest.TestCase):
    def test_load_and_write_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "set.jsonl"
            src.write_text("\n".join(json.dumps(r) for r in ROWS) + "\n\n", encoding="utf-8")
            self.assertEqual(load_eval_set(src), ROWS)

            records = run_eval(ROWS, ["m1"], perfect)["records"]
            out = write_results(records, Path(tmp) / "results")
            self.assertRegex(out.name, r"^run_\d{8}_\d{6}\.jsonl$")
            lines = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[0]["id"], "T01")
            self.assertEqual(lines[0]["deployment"], "m1")
            self.assertTrue(lines[0]["both_correct"])
            self.assertIn("latency_s", lines[0])

    def test_real_eval_set_loads(self):
        rows = load_eval_set()
        self.assertEqual(len(rows), 20)


if __name__ == "__main__":
    unittest.main()
