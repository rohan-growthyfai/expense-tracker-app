"""SQLite data layer for Spendly.

Three functions:
    get_db()   — a connection with dict-like rows and foreign keys enforced
    init_db()  — creates the tables (safe to run repeatedly)
    seed_db()  — inserts demo data for development (only once)

Run `python -m database.db` to build the database from scratch.
"""

import os
import sqlite3
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

# Absolute path to the repo root, so the database lands in the same place no
# matter which directory you run from. A bare "expense_tracker.db" would be
# relative to the current working directory and could create a second copy.
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)

# The only category values the app uses.
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    -- Stored as REAL. Production money code usually uses integer paise to
    -- avoid float rounding, but REAL keeps this app simple.
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    -- SQLite has no date type. ISO-8601 'YYYY-MM-DD' text sorts and compares
    -- correctly, and works with strftime() for monthly grouping later.
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    # Rows behave like dicts: row["email"] instead of row[2].
    conn.row_factory = sqlite3.Row
    # SQLite leaves foreign keys OFF by default, and the setting is per
    # connection — without this the FK below is never actually enforced.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create the tables. Safe to call multiple times."""
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def seed_db():
    """Insert demo data for development. Does nothing if users already exist."""
    conn = get_db()

    # Guard: if anyone is registered, the database is already in use.
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    # Werkzeug 3.x defaults to scrypt, which needs hashlib.scrypt — missing on
    # macOS system Python (LibreSSL). pbkdf2:sha256 works everywhere.
    password_hash = generate_password_hash("demo123", method="pbkdf2:sha256")

    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    # Dates counted back from today, so seed data is always recent and never
    # in the future — whatever day of the month the database is created on.
    today = date.today()

    def days_ago(n):
        return (today - timedelta(days=n)).isoformat()

    # Eight expenses covering all seven categories (Food appears twice).
    expenses = [
        (user_id, 450.00, "Food", days_ago(1), "Lunch with friends"),
        (user_id, 120.50, "Transport", days_ago(3), "Auto to office"),
        (user_id, 2200.00, "Bills", days_ago(6), "Electricity bill"),
        (user_id, 899.00, "Health", days_ago(9), "Pharmacy — monthly medicines"),
        (user_id, 650.00, "Entertainment", days_ago(12), "Movie tickets"),
        (user_id, 3499.00, "Shopping", days_ago(16), "Running shoes"),
        (user_id, 1500.00, "Other", days_ago(20), "Gift for a friend"),
        (user_id, 780.25, "Food", days_ago(24), "Groceries for the week"),
    ]

    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        expenses,
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    seed_db()
    print("Database ready at", DB_PATH)
