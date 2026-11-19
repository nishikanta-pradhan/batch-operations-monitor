"""SQLite connection and schema management."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    schedule_time TEXT NOT NULL,
    sla_time TEXT NOT NULL,
    expected_duration_minutes INTEGER NOT NULL CHECK (expected_duration_minutes > 0),
    criticality TEXT NOT NULL CHECK (criticality IN ('low', 'medium', 'high', 'critical')),
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS executions (
    execution_id TEXT PRIMARY KEY,
    job_name TEXT NOT NULL,
    business_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    records_processed INTEGER NOT NULL DEFAULT 0 CHECK (records_processed >= 0),
    error_message TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_name) REFERENCES jobs(job_name)
);

CREATE INDEX IF NOT EXISTS idx_executions_job_date
ON executions(job_name, business_date, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_executions_business_date
ON executions(business_date, status);
"""


class Database:
    """Owns SQLite connections while keeping transaction boundaries explicit."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as connection:
            connection.executescript(SCHEMA)

