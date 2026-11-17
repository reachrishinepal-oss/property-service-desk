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

# A unit id is the building letter, a hyphen and the unit number: floors 1 to 5, four units per floor.
BUILDINGS = {"A": "Contoso Heights A", "B": "Contoso Heights B", "G": "Contoso Gardens"}

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
CREATE TABLE buildings (code TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE units (unit TEXT PRIMARY KEY, building TEXT NOT NULL REFERENCES buildings(code));
CREATE TABLE residents (unit TEXT PRIMARY KEY REFERENCES units(unit), name TEXT NOT NULL);
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit TEXT NOT NULL REFERENCES units(unit),
    category TEXT NOT NULL,
    urgency TEXT NOT NULL,
    summary TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT
);
"""


def seed(path: Path) -> None:
    """Create the database at path with 3 buildings, 60 units, 60 residents and 40 tickets from the last 90 days."""
    rng = random.Random(3)  # fixed seed, so every fresh database holds the same invented data
    now = datetime.now()
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO buildings VALUES (?, ?)", BUILDINGS.items())
    units = [f"{code}-{floor}{number:02d}" for code in BUILDINGS for floor in range(1, 6) for number in range(1, 5)]
    for unit in units:
        db.execute("INSERT INTO units VALUES (?, ?)", (unit, unit[0]))
        db.execute("INSERT INTO residents VALUES (?, ?)",
                   (unit, f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_INITIALS)}."))
    for _ in range(40):
        category = rng.choice(CATEGORIES)
        created = now - timedelta(days=rng.uniform(0, 90))
        closed = created + timedelta(days=rng.uniform(0.2, 6))
        is_closed = closed < now and rng.random() < 0.7
        db.execute(
            "INSERT INTO tickets (unit, category, urgency, summary, status, created_at, closed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rng.choice(units), category, rng.choice(URGENCIES), SUMMARIES[category],
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


def find_resident(unit: str) -> dict | None:
    """Return the resident's name and building for a unit, or None if the unit does not exist."""
    with connect() as db:
        row = db.execute(
            "SELECT residents.name, buildings.name AS building FROM residents"
            " JOIN units USING (unit) JOIN buildings ON buildings.code = units.building"
            " WHERE residents.unit = ?", (unit,)).fetchone()
    return dict(row) if row else None


def insert_ticket(unit: str, category: str, urgency: str, summary: str) -> int:
    """Write an open ticket and return its id."""
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO tickets (unit, category, urgency, summary, status, created_at)"
            " VALUES (?, ?, ?, ?, 'open', ?)",
            (unit, category, urgency, summary, datetime.now().isoformat(timespec="seconds")))
    return cursor.lastrowid
