"""
PURPOSE: Prove the work-order tools check their arguments before acting: unknown unit, unknown label, empty summary.
LAYER:   Orchestration/Action
SESSION: S03
Run:     python -m unittest   (from the capstone folder; no Azure calls)
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mock_systems import work_orders
from src.tools.work_order_tools import create_ticket, get_resident


class WorkOrderToolTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db_path = Path(self.folder.name) / "work_orders.db"
        patcher = mock.patch.object(work_orders, "DB_PATH", self.db_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.folder.cleanup)

    def ticket_count(self) -> int:
        with sqlite3.connect(self.db_path) as db:
            return db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]

    def test_seed_has_60_residents_and_40_tickets(self):
        work_orders.connect().close()
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM residents").fetchone()[0], 60)
        self.assertEqual(self.ticket_count(), 40)

    def test_get_resident_returns_name_and_building_only(self):
        result = get_resident("a-101")
        self.assertEqual(set(result), {"name", "building"})
        self.assertEqual(result["building"], "Contoso Heights A")

    def test_get_resident_unknown_unit_is_an_error(self):
        self.assertIn("error", get_resident("1204"))

    def test_create_ticket_writes_a_row_and_returns_its_id(self):
        result = create_ticket("plumbing", "urgent", "G-302", "Leak under the sink.")
        self.assertEqual(result, {"ticket_id": 41})
        self.assertEqual(self.ticket_count(), 41)

    def test_create_ticket_rejects_bad_arguments_without_writing(self):
        bad_calls = [
            ("plumbing", "urgent", "1204", "Leak under the sink."),   # unknown unit
            ("roofing", "urgent", "A-101", "Leak under the sink."),   # unknown category
            ("plumbing", "asap", "A-101", "Leak under the sink."),    # unknown urgency
            ("plumbing", "urgent", "A-101", "   "),                   # empty summary
        ]
        for arguments in bad_calls:
            with self.subTest(arguments=arguments):
                self.assertIn("error", create_ticket(*arguments))
        self.assertEqual(self.ticket_count(), 40)


if __name__ == "__main__":
    unittest.main()
