"""
PURPOSE: Prove the plain-pandas check counts tickets per category in the last 30 days and averages days open of closed tickets.
LAYER:   Orchestration/Action
SESSION: S03
Run:     python -m unittest   (from the capstone folder; no Azure calls)
"""
from __future__ import annotations

import unittest
from datetime import datetime

import pandas as pd

from src.tools.manager_analytics import compute_test_answer

NOW = datetime(2026, 11, 17, 12, 0)
TICKETS = pd.DataFrame([
    {"category": "plumbing", "created_at": "2026-11-10T12:00:00", "closed_at": "2026-11-12T12:00:00"},  # 2 days open
    {"category": "plumbing", "created_at": "2026-11-01T12:00:00", "closed_at": None},                   # still open
    {"category": "hvac", "created_at": "2026-10-20T00:00:00", "closed_at": "2026-10-24T00:00:00"},      # 4 days open
    {"category": "noise", "created_at": "2026-09-01T12:00:00", "closed_at": "2026-09-01T18:00:00"},     # 0.25 days, too old to count
])


class ComputeTestAnswerTests(unittest.TestCase):
    def test_counts_only_tickets_from_the_last_30_days(self):
        result = compute_test_answer(TICKETS, NOW)
        self.assertEqual(result["tickets_per_category_last_30_days"], {"hvac": 1, "plumbing": 2})

    def test_averages_days_open_of_closed_tickets_only(self):
        result = compute_test_answer(TICKETS, NOW)
        self.assertEqual(result["average_days_open_closed_tickets"], round((2 + 4 + 0.25) / 3, 2))


if __name__ == "__main__":
    unittest.main()
