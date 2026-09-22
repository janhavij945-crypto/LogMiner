"""
log_repository.py
Implements the LogRepository class from the LogMiner Class Diagram.
Responsible for persisting and retrieving:
  - uploaded log files (metadata)
  - parsed log entries
  - detected anomalies
  - root-cause insights
  - exported reports
Storage engine: SQLite (file: logminer.db) -> satisfies "Persistent Storage:
Local filesystem" constraint from the SRS (section 2.4) while still giving a
real relational schema for the Database Design section.
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "logminer.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS log_files (
    file_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name       TEXT NOT NULL,
    storage_path    TEXT NOT NULL,
    uploaded_at     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Uploaded',
    total_lines     INTEGER DEFAULT 0,
    skipped_lines   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS log_entries (
    entry_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         INTEGER NOT NULL REFERENCES log_files(file_id),
    line_no         INTEGER NOT NULL,
    timestamp       TEXT,
    severity        TEXT,
    source          TEXT,
    message         TEXT,
    template_id     TEXT
);

CREATE TABLE IF NOT EXISTS log_templates (
    template_id     TEXT PRIMARY KEY,
    file_id         INTEGER NOT NULL REFERENCES log_files(file_id),
    pattern         TEXT NOT NULL,
    frequency       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         INTEGER NOT NULL REFERENCES log_files(file_id),
    window_start    TEXT NOT NULL,
    window_end      TEXT NOT NULL,
    anomaly_score   REAL NOT NULL,
    event_count     INTEGER,
    error_count     INTEGER,
    error_rate      REAL,
    top_templates   TEXT
);

CREATE TABLE IF NOT EXISTS incidents (
    incident_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         INTEGER NOT NULL REFERENCES log_files(file_id),
    root_cause_msg  TEXT,
    root_cause_time TEXT,
    severity        TEXT,
    evidence        TEXT,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS reports (
    report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id         INTEGER NOT NULL REFERENCES log_files(file_id),
    report_path     TEXT NOT NULL,
    generated_at    TEXT NOT NULL
);
"""


class LogRepository:
    """Maps to LogRepository in the Class Diagram: saveLog(), retrieveLog()."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._connect()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    # ---- Log file lifecycle -------------------------------------------------
    def save_log(self, file_name: str, storage_path: str) -> int:
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO log_files (file_name, storage_path, uploaded_at, status) "
            "VALUES (?, ?, ?, 'Uploaded')",
            (file_name, storage_path, datetime.now().isoformat()),
        )
        conn.commit()
        file_id = cur.lastrowid
        conn.close()
        return file_id

    def update_file_stats(self, file_id: int, total_lines: int, skipped_lines: int, status: str):
        conn = self._connect()
        conn.execute(
            "UPDATE log_files SET total_lines=?, skipped_lines=?, status=? WHERE file_id=?",
            (total_lines, skipped_lines, status, file_id),
        )
        conn.commit()
        conn.close()

    def retrieve_log(self, file_id: int):
        conn = self._connect()
        row = conn.execute("SELECT * FROM log_files WHERE file_id=?", (file_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    # ---- Parsed entries / templates -----------------------------------------
    def save_entries(self, file_id: int, entries: list):
        conn = self._connect()
        conn.executemany(
            "INSERT INTO log_entries (file_id, line_no, timestamp, severity, source, message, template_id) "
            "VALUES (:file_id, :line_no, :timestamp, :severity, :source, :message, :template_id)",
            [{**e, "file_id": file_id} for e in entries],
        )
        conn.commit()
        conn.close()

    def save_templates(self, file_id: int, templates: dict):
        conn = self._connect()
        conn.executemany(
            "INSERT OR REPLACE INTO log_templates (template_id, file_id, pattern, frequency) VALUES (?, ?, ?, ?)",
            [(tid, file_id, t["pattern"], t["frequency"]) for tid, t in templates.items()],
        )
        conn.commit()
        conn.close()

    # ---- Anomalies / incidents -----------------------------------------------
    def save_anomalies(self, file_id: int, anomalies: list):
        conn = self._connect()
        conn.executemany(
            "INSERT INTO anomalies (file_id, window_start, window_end, anomaly_score, "
            "event_count, error_count, error_rate, top_templates) VALUES "
            "(:file_id, :window_start, :window_end, :anomaly_score, :event_count, "
            ":error_count, :error_rate, :top_templates)",
            [{**a, "file_id": file_id, "top_templates": json.dumps(a["top_templates"])} for a in anomalies],
        )
        conn.commit()
        conn.close()

    def save_incident(self, file_id: int, incident: dict) -> int:
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO incidents (file_id, root_cause_msg, root_cause_time, severity, evidence, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                file_id,
                incident["root_cause_msg"],
                incident["root_cause_time"],
                incident["severity"],
                json.dumps(incident["evidence"]),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        incident_id = cur.lastrowid
        conn.close()
        return incident_id

    def get_anomalies(self, file_id: int):
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM anomalies WHERE file_id=? ORDER BY anomaly_score DESC", (file_id,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_incidents(self, file_id: int):
        conn = self._connect()
        rows = conn.execute("SELECT * FROM incidents WHERE file_id=?", (file_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---- Reports ---------------------------------------------------------
    def save_report(self, file_id: int, report_path: str) -> int:
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO reports (file_id, report_path, generated_at) VALUES (?, ?, ?)",
            (file_id, report_path, datetime.now().isoformat()),
        )
        conn.commit()
        report_id = cur.lastrowid
        conn.close()
        return report_id
