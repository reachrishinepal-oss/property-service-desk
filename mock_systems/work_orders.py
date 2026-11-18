"""
PURPOSE: A mock work-order system in SQLite: buildings, units, residents and tickets, all invented.
LAYER:   Data/Knowledge (a stand-in for the property manager's real system)
SESSION: S03
"""
from __future__ import annotations

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from src.intelligence.triage import CATEGORIES, URGENCIES

DB_PATH = Path(__file__).with_name("work_orders.db")  # git-ignored; created on first use

# A unit is identified by two separate values, its building and its unit number, never by one combined id.
# Unit numbers are text, so "300" and "300A" are different units.
BUILDINGS = ("Contoso Heights A", "Contoso Heights B", "Contoso Gardens", "Contoso Arta", "Contoso Arta 2")
# Awkward units on purpose: 300 next to 300A, and 300 in "Contoso Arta 2" next to 2300 in "Contoso Arta".
SPECIAL_UNITS = {"Contoso Heights B": ["300", "300A"], "Contoso Arta": ["2300"], "Contoso Arta 2": ["300"]}

FIRST_NAMES = ["Layla", "Omar", "Aisha", "Yusuf", "Mariam", "Karim", "Noor", "Hassan", "Sara", "Tariq",
               "Huda", "Rami", "Dana", "Faris", "Lina", "Samir", "Reem", "Adil", "Maya", "Ziad"]
LAST_INITIALS = "ABDFHJKMNRSTWZ"

SUMMARIES = {
    "plumbing": "Water leaking under the kitchen sink.",
    "electrical": "Bedroom sockets stopped working.",
    "hvac": "Air conditioning blows warm air.",
    "appliance": "Washing machine will not drain.",
    "pest": "Cockroaches seen in the kitchen.",
    "noise": "Loud music from the unit above late at night.",
    "access_security": "Key fob no longer opens the lobby door.",
    "common_area": "Pool area light is broken.",
    "lease_billing": "Question about a charge on the service fee invoice.",
}

SCHEMA = """
CREATE TABLE residents (
    building TEXT NOT NULL,
    unit_number TEXT NOT NULL,
    name TEXT NOT NULL,
    PRIMARY KEY (building, unit_number)
);
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building TEXT NOT NULL,
    unit_number TEXT NOT NULL,
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    FOREIGN KEY (building, unit_number) REFERENCES residents (building, unit_number)
);
"""


def unit_numbers(building: str) -> list[str]:
    """Twelve unit numbers per building: floors 1 to 3, four units each, with the building's awkward units in place of the last ones."""
    regular = [f"{floor}{number:02d}" for floor in range(1, 4) for number in range(1, 5)]
    special = SPECIAL_UNITS.get(building, [])
    return regular[:12 - len(special)] + special


def seed(path: Path) -> None:
    """Create the database at path with 5 buildings, 60 units (one resident each) and 40 tickets from the last 90 days."""
    rng = random.Random(3)  # fixed seed, so every fresh database holds the same invented data
    now = datetime.now()
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    units = [(building, number) for building in BUILDINGS for number in unit_numbers(building)]
    for building, number in units:
        db.execute("INSERT INTO residents VALUES (?, ?, ?)",
                   (building, number, f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}."))
    for _ in range(40):
        category = rng.choice(CATEGORIES)
        created = now - timedelta(days=rng.uniform(0, 90))
        closed = created + timedelta(days=rng.uniform(0.2, 6))
        is_closed = closed < now and rng.random() < 0.7
        db.execute(
            "INSERT INTO tickets (building, unit_number, category, urgency, summary, status, created_at, closed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (*rng.choice(units), category, rng.choice(URGENCIES), SUMMARIES[category],
             "closed" if is_closed else "open", created.isoformat(timespec="seconds"),
             closed.isoformat(timespec="seconds") if is_closed else None),
        )
    db.commit()
    db.close()


def connect() -> sqlite3.Connection:
    """Open the work-order database, seeding it first if the file does not exist yet."""
    if not DB_PATH.exists():
        seed(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def find_resident(building: str, unit_number: str) -> dict | None:
    """Return the resident's name and building for the (building, unit_number) pair, or None if that unit does not exist."""
    with connect() as db:
        row = db.execute("SELECT name, building FROM residents WHERE building = ? AND unit_number = ?",
                         (building, unit_number)).fetchone()
    return dict(row) if row else None


def insert_ticket(building: str, unit_number: str, category: str, urgency: str, summary: str) -> int:
    """Write an open ticket and return its id."""
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO tickets (building, unit_number, category, urgency, summary, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'open', ?)",
            (building, unit_number, category, urgency, summary, datetime.now().isoformat(timespec="seconds")))
    return cursor.lastrowid


def read_tickets() -> list[dict]:
    """Return every ticket row, oldest first."""
    with connect() as db:
        rows = db.execute("SELECT id, building, unit_number, category, urgency, summary, status, created_at, closed_at"
                          " FROM tickets ORDER BY id").fetchall()
    return [dict(row) for row in rows]
