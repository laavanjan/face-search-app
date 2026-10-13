"""SQLite store for governance records: audit log, review cases, appeals,
operator controls and approved configuration baselines.

Kept separate from Qdrant so oversight records survive a re-index and can be
retained/purged on their own schedule (governance/data-retention-policy.yaml).
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

_lock = threading.RLock()
_conn: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    actor TEXT NOT NULL,
    roles TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log(ts);

CREATE TABLE IF NOT EXISTS review_cases (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    requested_by TEXT NOT NULL,
    status TEXT NOT NULL,
    threshold REAL NOT NULL,
    query_faces INTEGER NOT NULL,
    query_image BLOB,
    query_media_type TEXT,
    closed_by TEXT,
    closed_at REAL,
    close_reason TEXT
);

CREATE TABLE IF NOT EXISTS review_candidates (
    case_id TEXT NOT NULL REFERENCES review_cases(id) ON DELETE CASCADE,
    face_id TEXT NOT NULL,
    photo_id TEXT NOT NULL,
    score REAL,
    bbox TEXT NOT NULL,
    source TEXT NOT NULL,
    decision TEXT NOT NULL,
    decided_by TEXT,
    decided_at REAL,
    reason TEXT,
    PRIMARY KEY (case_id, face_id)
);

CREATE TABLE IF NOT EXISTS appeals (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    category TEXT NOT NULL,
    photo_id TEXT,
    face_id TEXT,
    case_id TEXT,
    reason TEXT NOT NULL,
    contact TEXT,
    status TEXT NOT NULL,
    ack_by REAL NOT NULL,
    resolve_by REAL NOT NULL,
    outcome TEXT,
    resolution TEXT,
    resolved_by TEXT,
    resolved_at REAL
);

CREATE TABLE IF NOT EXISTS controls (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at REAL NOT NULL,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS config_baselines (
    fingerprint TEXT PRIMARY KEY,
    snapshot TEXT NOT NULL,
    change_id TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at REAL NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        c = sqlite3.connect(get_settings().db_path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        c.executescript(SCHEMA)
        _conn = c
    return _conn


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    with _lock:
        c = _connect()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def reset_for_tests() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None
