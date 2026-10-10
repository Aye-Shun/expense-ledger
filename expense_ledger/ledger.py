"""Input validation and parameterized SQLite queries."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import re
import sqlite3


# SQLite stores signed 64-bit integers. Keep aggregate amounts in that range too.
MAX_CENTS = 2**63 - 1


def parse_amount(value):
    """Convert a positive decimal amount to integer cents without rounding."""
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", text):
        raise ValueError("amount must be positive with at most two decimal places")
    # Decimal preserves the written amount; no floating-point conversion is used.
    decimal_amount = Decimal(text)
    if decimal_amount > Decimal("92233720368547758.07"):
        raise ValueError("amount must fit in a SQLite integer")
    cents = int(decimal_amount * 100)
    if not 0 < cents <= MAX_CENTS:
        raise ValueError("amount must be positive and fit in a SQLite integer")
    return cents


def parse_date(value):
    """Require a real calendar date in the unambiguous YYYY-MM-DD format."""
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("date must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("date must be a real calendar date") from exc


def parse_month(value):
    """Return a validated YYYY-MM prefix for filtering and grouping."""
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
        raise ValueError("month must use YYYY-MM")
    parse_date(value + "-01")
    return value


def normalize_category(value):
    category = value.strip().casefold()
    if not category or len(category) > 40 or not category.isprintable():
        raise ValueError("category must contain 1–40 printable characters")
    return category


def validate_note(value):
    note = value.strip()
    if len(note) > 200 or (note and not note.isprintable()):
        raise ValueError("note must contain at most 200 printable characters")
    return note


def format_amount(cents):
    """Format cents exactly, including amounts beyond float precision."""
    return f"{cents // 100}.{cents % 100:02d}"


@contextmanager
def connect(path):
    """Open/create a local database and always close its connection."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT ''
            )"""
        )
        connection.commit()
        yield connection
    finally:
        connection.close()


def add_expense(connection, amount, category, spent_on, note=""):
    cents = parse_amount(amount)
    category = normalize_category(category)
    spent_on = parse_date(spent_on)
    note = validate_note(note)
    with connection:
        # Lock before checking the total so simultaneous CLI calls cannot bypass
        # the cap. Python integers avoid overflow while adding existing rows.
        connection.execute("BEGIN IMMEDIATE")
        existing_total = sum(
            row[0] for row in connection.execute("SELECT amount_cents FROM expenses")
        )
        if existing_total + cents > MAX_CENTS:
            raise ValueError("ledger total would exceed SQLite's integer limit")
        cursor = connection.execute(
            """INSERT INTO expenses (amount_cents, category, spent_on, note)
               VALUES (?, ?, ?, ?)""",
            (cents, category, spent_on, note),
        )
    return cursor.lastrowid


def list_expenses(connection, month=None, category=None):
    month = parse_month(month) if month is not None else None
    category = normalize_category(category) if category is not None else None
    return connection.execute(
        """SELECT id, spent_on, category, amount_cents, note FROM expenses
           WHERE (? IS NULL OR substr(spent_on, 1, 7) = ?)
             AND (? IS NULL OR category = ?)
           ORDER BY spent_on, id""",
        (month, month, category, category),
    ).fetchall()


def summarize(connection, month=None):
    month = parse_month(month) if month is not None else None
    return connection.execute(
        """SELECT substr(spent_on, 1, 7) AS month, category,
                  COUNT(*) AS count, SUM(amount_cents) AS total_cents
           FROM expenses
           WHERE (? IS NULL OR substr(spent_on, 1, 7) = ?)
           GROUP BY substr(spent_on, 1, 7), category
           ORDER BY month, category""",
        (month, month),
    ).fetchall()
