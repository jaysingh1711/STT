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
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at     TEXT NOT NULL,
                transcript     TEXT NOT NULL,
                diagnosis      TEXT,
                symptoms       TEXT,
                follow_up      TEXT,
                medications    TEXT,
                patient_name   TEXT,
                patient_age    TEXT,
                patient_gender TEXT
            )
        """)
        conn.commit()

        # Migration: if records.db already existed before this update,
        # the CREATE TABLE above is a no-op (table already exists) and
        # won't add the new columns. This adds them safely if missing.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(records)")}
        migrations = {
            "patient_name":   "ALTER TABLE records ADD COLUMN patient_name TEXT",
            "patient_age":    "ALTER TABLE records ADD COLUMN patient_age TEXT",
            "patient_gender": "ALTER TABLE records ADD COLUMN patient_gender TEXT",
        }
        for col, ddl in migrations.items():
            if col not in existing_cols:
                conn.execute(ddl)
                logger.info(f"Migrated records table: added column '{col}'")
        conn.commit()

        logger.info(f"Database ready at {DB_PATH}")
    finally:
        conn.close()


def save_record(transcript: str, diagnosis: str, symptoms: str,
                follow_up: str, medications: list,
                patient_name: str = "", patient_age: str = "",
                patient_gender: str = "") -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO records (
                created_at, transcript, diagnosis, symptoms, follow_up,
                medications, patient_name, patient_age, patient_gender
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                transcript,
                diagnosis,
                symptoms,
                follow_up,
                json.dumps(medications),
                patient_name,
                patient_age,
                patient_gender,
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