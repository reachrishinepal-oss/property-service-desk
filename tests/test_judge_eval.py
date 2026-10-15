"""
PURPOSE: Prove the judge eval runner loads the set, writes a replies file the evaluators can read, and summarises scores.
LAYER:   Evaluation/Reliability
SESSION: S01
Run:     python -m unittest   (from the capstone folder)
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.governance.judge_eval import (
    EvalNotValid,
    generate_replies,
    load_eval_requests,
    merge_judge_results,
    read_replies,
    screen_replies,
    summarise,
    write_judge_results,
    write_replies,
)

ROWS = [
    {"id": "T01", "text": "Water through the ceiling", "expected_category": "plumbing",
     "expected_urgency": "emergency", "hard": False, "note": "active leak"},
    {"id": "T02", "text": "Gym treadmill is broken", "expected_category": "common_area",
     "expected_urgency": "routine", "hard": False, "note": "shared space"},
]


def echo(text: str) -> str:
    return f"Thank you, we have logged: {text}"


def fails_on_gym(text: str) -> str:
    if "Gym" in text:
        raise RuntimeError("endpoint unavailable")
    return echo(text)


class LoadTests(unittest.TestCase):
    def test_load_keeps_only_id_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "set.jsonl"
            src.write_text("\n".join(json.dumps(r) for r in ROWS) + "\n\n", encoding="utf-8")
            self.assertEqual(
                load_eval_requests(src),
                [{"id": "T01", "text": "Water through the ceiling"},
                 {"id": "T02", "text": "Gym treadmill is broken"}],
            )

    def test_real_eval_set_loads(self):
        rows = load_eval_requests()
        self.assertEqual(len(rows), 20)
        self.assertTrue(all(set(r) == {"id", "text"} and r["text"] for r in rows))


class ReplyTests(unittest.TestCase):
    def test_error_on_one_row_does_not_stop_the_run(self):
        records = generate_replies(load_rows(), fails_on_gym)
        self.assertEqual([r["id"] for r in records], ["T01", "T02"])
        self.assertIsNone(records[0]["error"])
        self.assertEqual(records[0]["response"], echo("Water through the ceiling"))
        self.assertIn("endpoint unavailable", records[1]["error"])
        self.assertEqual(records[1]["response"], "")

    def test_not_implemented_stops_the_run(self):
        def unfinished(text):
            raise NotImplementedError("LZ-00.3")

        with self.assertRaises(NotImplementedError):
            generate_replies(load_rows(), unfinished)

    def test_replies_file_round_trip_has_query_and_response_on_every_line(self):
        records = generate_replies(load_rows(), fails_on_gym)
        records.append({"id": "T99", "query": "Hand-made row", "response": None, "error": "boom"})
        with tempfile.TemporaryDirectory() as tmp:
            path = write_replies(records, Path(tmp) / "results")
            self.assertRegex(path.name, r"^replies_\d{8}_\d{6}\.jsonl$")
            lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertIn("query", line)
            self.assertIn("response", line)
            self.assertIsInstance(line["response"], str)
        self.assertEqual(lines[0]["query"], "Water through the ceiling")
        self.assertEqual(lines[0]["id"], "T01")
        self.assertEqual(lines[2]["response"], "")


def load_rows() -> list[dict]:
    return [{"id": r["id"], "text": r["text"]} for r in ROWS]


def batch(total: int, failed: int) -> list[dict]:
    """Make total reply records, the first `failed` of them with an error."""
    return [
        {"id": f"T{i:02d}", "query": f"q{i}", "response": "" if i < failed else f"reply {i}",
         "error": "RuntimeError: boom" if i < failed else None}
        for i in range(total)
    ]


class ScreenTests(unittest.TestCase):
    def test_failed_replies_are_left_out_and_counted(self):
        kept, messages = screen_replies(batch(20, 1))
        self.assertEqual(len(kept), 19)
        self.assertTrue(all(r["error"] is None for r in kept))
        self.assertEqual(messages, ["1 of 20 replies failed and were not judged."])

    def test_empty_response_without_error_counts_as_failed(self):
        records = batch(20, 0)
        records[5]["response"] = "   "
        records[6].pop("error")
        records[6]["response"] = None
        kept, messages = screen_replies(records)
        self.assertEqual(len(kept), 18)
        self.assertEqual(messages[0], "2 of 20 replies failed and were not judged.")

    def test_no_failures_reports_zero(self):
        kept, messages = screen_replies(batch(20, 0))
        self.assertEqual(len(kept), 20)
        self.assertEqual(messages, ["0 of 20 replies failed and were not judged."])

    def test_exactly_ten_percent_does_not_warn(self):
        _, messages = screen_replies(batch(20, 2))
        self.assertEqual(len(messages), 1)

    def test_above_ten_percent_warns(self):
        kept, messages = screen_replies(batch(20, 3))
        self.assertEqual(len(kept), 17)
        self.assertEqual(messages[0], "3 of 20 replies failed and were not judged.")
        self.assertTrue(messages[1].startswith("WARNING: 15%"))

    def test_exactly_twenty_percent_warns_but_does_not_stop(self):
        kept, messages = screen_replies(batch(20, 4))
        self.assertEqual(len(kept), 16)
        self.assertIn("WARNING", messages[1])

    def test_above_twenty_percent_stops_as_not_valid(self):
        with self.assertRaises(EvalNotValid) as ctx:
            screen_replies(batch(20, 5))
        self.assertIn("5 of 20 replies failed", str(ctx.exception))
        self.assertIn("not valid", str(ctx.exception))

    def test_all_failed_stops(self):
        with self.assertRaises(EvalNotValid):
            screen_replies(batch(3, 3))

    def test_no_replies_stops(self):
        with self.assertRaises(EvalNotValid):
            screen_replies([])

    def test_thresholds_can_be_overridden(self):
        _, messages = screen_replies(batch(20, 1), warn_above=0.0, stop_above=0.5)
        self.assertIn("WARNING", messages[1])

    def test_judged_file_holds_only_kept_replies(self):
        with tempfile.TemporaryDirectory() as tmp:
            replies = write_replies(batch(20, 3), tmp)
            kept, _ = screen_replies(read_replies(replies))
            judged = write_replies(kept, tmp, prefix="judged")
            self.assertRegex(judged.name, r"^judged_\d{8}_\d{6}\.jsonl$")
            self.assertEqual(len(read_replies(replies)), 20)
            self.assertEqual([r["id"] for r in read_replies(judged)], [f"T{i:02d}" for i in range(3, 20)])


RESULT = {
    "rows": [
        {"id": "T01", "relevance": 5, "relevance_reason": "Directly addresses the leak.",
         "coherence": 4, "coherence_reason": "Clear order.", "fluency": 5, "fluency_reason": "Fluent."},
        {"id": "T02", "relevance": 2, "relevance_reason": "Talks about rent instead of the gym " * 5,
         "coherence": 3, "coherence_reason": "Jumps between topics.", "fluency": 4, "fluency_reason": "Fine."},
        {"id": "T03", "relevance": 3, "relevance_reason": "Partly on topic.",
         "coherence": 5, "coherence_reason": "Good.", "fluency": 5, "fluency_reason": "Fluent."},
        {"id": "T04", "relevance": 4, "relevance_reason": "Mostly on topic.",
         "coherence": None, "coherence_reason": None, "fluency": 1, "fluency_reason": "Garbled."},
    ],
    "metrics": {"relevance": 3.5, "coherence": 4.0, "fluency": 3.75},
}


class SummariseTests(unittest.TestCase):
    def setUp(self):
        self.text = summarise(RESULT)
        self.lines = self.text.splitlines()

    def row_for(self, name: str) -> list[str]:
        return next(line for line in self.lines if line.startswith(name)).split()

    def test_one_row_per_evaluator_with_average_and_good_count(self):
        self.assertEqual(self.row_for("relevance"), ["relevance", "3.50", "2/4", "4"])
        self.assertEqual(self.row_for("coherence"), ["coherence", "4.00", "2/3", "3"])
        self.assertEqual(self.row_for("fluency"), ["fluency", "3.75", "3/4", "4"])

    def test_lowest_three_rows_listed_lowest_first_with_short_reasons(self):
        block = self.text.split("Lowest relevance:")[1].split("Lowest coherence:")[0]
        ids = [line.split()[0] for line in block.strip().splitlines()]
        self.assertEqual(ids, ["T02", "T03", "T04"])
        self.assertNotIn("T01", block)
        long_line = next(line for line in block.splitlines() if "T02" in line)
        self.assertTrue(long_line.endswith("..."))
        self.assertLess(len(long_line), 120)

    def test_average_computed_when_metrics_missing(self):
        text = summarise({"rows": RESULT["rows"]})
        row = next(line for line in text.splitlines() if line.startswith("relevance")).split()
        self.assertEqual(row[1], "3.50")

    def test_empty_result_does_not_crash(self):
        text = summarise({"rows": [], "metrics": {}})
        self.assertIn("n/a", text)

    def test_write_judge_results_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_judge_results(RESULT, Path(tmp) / "results")
            self.assertRegex(path.name, r"^judge_\d{8}_\d{6}\.json$")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), RESULT)



class MergeJudgeResultsTest(unittest.TestCase):
    def test_rescored_rows_replace_nulls_and_averages_cover_all_rows(self):
        earlier = {"rows": [
            {"id": "T01", "relevance": 4.0, "coherence": 4.0, "fluency": 4.0},
            {"id": "T02", "relevance": None, "coherence": None, "fluency": None},
            {"id": "T03", "relevance": None, "coherence": None, "fluency": None},
        ]}
        rescored = {"rows": [
            {"id": "T02", "relevance": 2.0, "coherence": 3.0, "fluency": 5.0},
            {"id": "T03", "relevance": None, "coherence": None, "fluency": None, "judge_error": "Timeout"},
        ]}
        merged = merge_judge_results(earlier, rescored)
        self.assertEqual([r["id"] for r in merged["rows"]], ["T01", "T02", "T03"])
        self.assertEqual(merged["rows"][2]["judge_error"], "Timeout")
        self.assertEqual(merged["metrics"], {"relevance": 3.0, "coherence": 3.5, "fluency": 4.5})


if __name__ == "__main__":
    unittest.main()
