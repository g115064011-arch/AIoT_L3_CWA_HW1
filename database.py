# database.py
# This module manages the SQLite database stored in data/weather.db.
# It handles creating the table, inserting weather forecast records,
# and querying stored data for display in the Streamlit web app.
# All operations use Python's built-in sqlite3 library and raw SQL.

import os
import sqlite3

# Path to the SQLite database file (relative to project root)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "weather.db")

# SQL: Create the weather_forecasts table if it doesn't already exist.
# UNIQUE constraint on (locationName, startTime, endTime) prevents duplicate rows
# when the same API response is fetched and inserted more than once.
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weather_forecasts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    locationName TEXT    NOT NULL,
    startTime    TEXT    NOT NULL,
    endTime      TEXT    NOT NULL,
    Wx           TEXT,
    MinT         REAL,
    MaxT         REAL,
    UNIQUE (locationName, startTime, endTime)
);
"""

# SQL: Insert one forecast record.
# INSERT OR IGNORE skips the row silently if the UNIQUE constraint is violated,
# so re-running the pipeline never produces duplicate rows.
INSERT_SQL = """
INSERT OR IGNORE INTO weather_forecasts
    (locationName, startTime, endTime, Wx, MinT, MaxT)
VALUES
    (:locationName, :startTime, :endTime, :Wx, :MinT, :MaxT);
"""

# SQL: Select all stored records, ordered by location then time.
SELECT_ALL_SQL = """
SELECT id, locationName, startTime, endTime, Wx, MinT, MaxT
FROM weather_forecasts
ORDER BY locationName, startTime;
"""


def get_connection():
    """
    Open and return a connection to the SQLite database.
    The data/ directory is created automatically if it does not exist.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows behave like dicts
    return conn


def init_db():
    """
    Create the database file and the weather_forecasts table if they
    do not already exist. Safe to call multiple times (idempotent).
    """
    conn = get_connection()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        print(f"[DB]  Database ready  : {DB_PATH}")
        print( "[DB]  Table ready     : weather_forecasts")
    finally:
        conn.close()


def insert_records(forecast_records):
    """
    Insert a list of forecast dicts into the weather_forecasts table.
    Duplicate rows (same locationName + startTime + endTime) are silently skipped.

    Args:
        forecast_records (list[dict]): Output from weather_api.parse_forecast().

    Returns:
        int: Number of rows actually inserted (excludes duplicates).
    """
    if not forecast_records:
        print("[DB]  No records to insert.")
        return 0

    conn = get_connection()
    try:
        # Convert MinT / MaxT from string to float for the REAL columns
        cleaned = []
        for rec in forecast_records:
            cleaned.append({
                "locationName": rec["locationName"],
                "startTime":    rec["startTime"],
                "endTime":      rec["endTime"],
                "Wx":           rec["Wx"],
                "MinT":         float(rec["MinT"]) if rec["MinT"] else None,
                "MaxT":         float(rec["MaxT"]) if rec["MaxT"] else None,
            })

        before = conn.execute("SELECT COUNT(*) FROM weather_forecasts").fetchone()[0]
        conn.executemany(INSERT_SQL, cleaned)
        conn.commit()
        after = conn.execute("SELECT COUNT(*) FROM weather_forecasts").fetchone()[0]

        inserted = after - before
        skipped  = len(forecast_records) - inserted
        print(f"[DB]  Records inserted : {inserted}")
        if skipped > 0:
            print(f"[DB]  Duplicates skipped: {skipped} (already in database)")
        return inserted
    finally:
        conn.close()


def get_all_records():
    """
    Query and return all rows from weather_forecasts, ordered by location and time.

    Returns:
        list[sqlite3.Row]: All stored forecast rows.
    """
    conn = get_connection()
    try:
        rows = conn.execute(SELECT_ALL_SQL).fetchall()
        return rows
    finally:
        conn.close()
