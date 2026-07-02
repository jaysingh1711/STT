"""
database.py
------------
SQLite database setup for saving prescription records locally.
SQLite is a file-based database -- no separate server needed, no
installation, no configuration. A single file (records.db) stores
everything. Perfect for a local/clinic deployment.
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("database")

DB_PATH = Path(__file__).parent / "records.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                transcript  TEXT NOT NULL,
                diagnosis   TEXT,
                symptoms    TEXT,
                follow_up   TEXT,
                medications TEXT
            )
        """)
        conn.commit()
        logger.info(f"Database ready at {DB_PATH}")
    finally:
        conn.close()


def save_record(transcript: str, diagnosis: str, symptoms: str,
                follow_up: str, medications: list) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO records (created_at, transcript, diagnosis, symptoms, follow_up, medications)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                transcript,
                diagnosis,
                symptoms,
                follow_up,
                json.dumps(medications),
            )
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.info(f"Record saved with ID {record_id}")
        return record_id
    finally:
        conn.close()


def get_record(record_id: int) -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["medications"] = json.loads(record["medications"] or "[]")
        return record
    finally:
        conn.close()


def get_all_records() -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM records ORDER BY created_at DESC"
        ).fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["medications"] = json.loads(record["medications"] or "[]")
            records.append(record)
        return records
    finally:
        conn.close()