import sqlite3
from pathlib import Path

DB_PATH = Path("data") / "weather.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_names(conn):
    rows = conn.execute(
        "PRAGMA table_info(weather_forecasts)"
    ).fetchall()
    return {row["name"] for row in rows}


def init_db():
    """Create / migrate the SQLite table safely."""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                locationName TEXT NOT NULL,
                startTime TEXT NOT NULL,
                endTime TEXT NOT NULL,
                Wx TEXT,
                MinT REAL,
                MaxT REAL,
                PoP REAL,
                CI TEXT
            )
            """
        )

        columns = _column_names(conn)

        if "PoP" not in columns:
            conn.execute(
                "ALTER TABLE weather_forecasts ADD COLUMN PoP REAL"
            )

        if "CI" not in columns:
            conn.execute(
                "ALTER TABLE weather_forecasts ADD COLUMN CI TEXT"
            )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_weather_unique
            ON weather_forecasts(locationName, startTime, endTime)
            """
        )

        conn.commit()


def replace_current_forecast(records):
    """
    Replace the stored forecast snapshot with the newest CWA response.

    For this 36-hour dashboard, keeping one clean current snapshot is clearer
    than mixing forecasts from several API fetches. It also removes old rows
    that were created by the previous parser.
    """
    if not records:
        return 0

    init_db()

    with _connect() as conn:
        conn.execute("DELETE FROM weather_forecasts")

        conn.executemany(
            """
            INSERT INTO weather_forecasts (
                locationName,
                startTime,
                endTime,
                Wx,
                MinT,
                MaxT,
                PoP,
                CI
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record.get("locationName"),
                    record.get("startTime"),
                    record.get("endTime"),
                    record.get("Wx"),
                    record.get("MinT"),
                    record.get("MaxT"),
                    record.get("PoP"),
                    record.get("CI"),
                )
                for record in records
            ],
        )

        conn.commit()

    return len(records)


# Keep this name for compatibility with earlier versions.
def insert_records(records):
    return replace_current_forecast(records)


def get_all_records():
    init_db()

    with _connect() as conn:
        return conn.execute(
            """
            SELECT
                id,
                locationName,
                startTime,
                endTime,
                Wx,
                MinT,
                MaxT,
                PoP,
                CI
            FROM weather_forecasts
            ORDER BY startTime, locationName
            """
        ).fetchall()
