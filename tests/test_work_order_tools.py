"""
PURPOSE: Prove the work-order tools check their arguments before acting (unknown unit, unknown label, empty summary) and never return a name.
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

    def test_get_resident_returns_the_building_and_no_name(self):
        self.assertEqual(get_resident("Contoso Heights A", "101"), {"building": "Contoso Heights A"})

    def test_get_resident_unknown_pair_is_an_error(self):
        self.assertIn("error", get_resident("Contoso Heights A", "1204"))
        self.assertIn("error", get_resident("Contoso Gardens", "300A"))  # 300A exists, but only in Contoso Heights B

    def test_similar_units_are_different_units(self):
        create_ticket("plumbing", "urgent", "Contoso Arta 2", "300", "Leak under the sink.")
        create_ticket("plumbing", "urgent", "Contoso Arta", "2300", "Leak under the sink.")
        create_ticket("electrical", "urgent", "Contoso Heights B", "300", "No power.")
        create_ticket("electrical", "urgent", "Contoso Heights B", "300A", "No power.")
        with sqlite3.connect(self.db_path) as db:
            new = db.execute("SELECT building, unit_number FROM tickets WHERE id > 40 ORDER BY id").fetchall()
        self.assertEqual(new, [("Contoso Arta 2", "300"), ("Contoso Arta", "2300"),
                               ("Contoso Heights B", "300"), ("Contoso Heights B", "300A")])

    def test_create_ticket_writes_a_row_and_returns_its_id(self):
        result = create_ticket("plumbing", "urgent", "Contoso Gardens", "302", "Leak under the sink.")
        self.assertEqual(result, {"ticket_id": 41, "building": "Contoso Gardens", "unit_number": "302"})
        self.assertEqual(self.ticket_count(), 41)

    def test_create_ticket_rejects_bad_arguments_without_writing(self):
        bad_calls = [
            ("plumbing", "urgent", "Contoso Arta", "300", "Leak under the sink."),     # unknown pair
            ("plumbing", "urgent", "Contoso Tower", "101", "Leak under the sink."),    # unknown building
            ("roofing", "urgent", "Contoso Heights A", "101", "Leak under the sink."), # unknown category
            ("plumbing", "asap", "Contoso Heights A", "101", "Leak under the sink."),   # unknown urgency
            ("plumbing", "urgent", "Contoso Heights A", "101", "   "),                 # empty summary
        ]
        for arguments in bad_calls:
            with self.subTest(arguments=arguments):
                self.assertIn("error", create_ticket(*arguments))
        self.assertEqual(self.ticket_count(), 40)


if __name__ == "__main__":
    unittest.main()
