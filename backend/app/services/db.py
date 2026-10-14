"""SQLite store for governance records: audit log, review cases, appeals,
operator controls and approved configuration baselines.

Kept separate from Qdrant so oversight records survive a re-index and can be
retained/purged on their own schedule (governance/data-retention-policy.yaml).
Every column, its reader/writer and its retention is listed in
governance/data-inventory.yaml; tests/test_governance.py fails on any column
missing from that inventory.
"""
from __future__ import annotations

import hashlib
import json
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
    detail TEXT,
    trace_id TEXT,
    rationale TEXT,
    prev_hash TEXT,
    row_hash TEXT
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
    access_hash TEXT,
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
        _migrate(c)
        _conn = c
    return _conn


# Columns added after the first release: (table, column, type).
_ADDED_COLUMNS = [
    ("audit_log", "trace_id", "TEXT"),
    ("audit_log", "rationale", "TEXT"),
    ("appeals", "access_hash", "TEXT"),
    ("audit_log", "prev_hash", "TEXT"),
    ("audit_log", "row_hash", "TEXT"),
]

# --- audit_log: append-only + hash chain (DOC-07) -----------------------------------
# UPDATE is always refused. DELETE is refused except for the oldest row, so the
# retention sweep can only expire the log from its head and the remaining rows
# stay one contiguous, verifiable chain (audit.verify_chain).
GENESIS = "0" * 64
AUDIT_HASHED_FIELDS = ("ts", "actor", "roles", "action", "target", "detail", "trace_id", "rationale")
_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_log_expire_oldest_only BEFORE DELETE ON audit_log
WHEN OLD.id != (SELECT MIN(id) FROM audit_log)
BEGIN SELECT RAISE(ABORT, 'audit_log rows may only be expired oldest-first'); END;
"""


def row_digest(prev_hash: str, row: dict) -> str:
    payload = json.dumps([prev_hash] + [row.get(f) for f in AUDIT_HASHED_FIELDS], sort_keys=True, default=repr)
    return hashlib.sha256(payload.encode()).hexdigest()


def _backfill_chain(c: sqlite3.Connection) -> None:
    if not c.execute("SELECT 1 FROM audit_log WHERE row_hash IS NULL LIMIT 1").fetchone():
        return
    c.execute("DROP TRIGGER IF EXISTS audit_log_no_update")
    prev = GENESIS
    for r in c.execute("SELECT * FROM audit_log ORDER BY id").fetchall():
        h = row_digest(prev, dict(r))
        c.execute("UPDATE audit_log SET prev_hash = ?, row_hash = ? WHERE id = ?", (prev, h, r["id"]))
        prev = h


def _migrate(c: sqlite3.Connection) -> None:
    for table, col, typ in _ADDED_COLUMNS:
        cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
        if col not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
    _backfill_chain(c)
    c.executescript(_TRIGGERS)
    from app.version import DB_SCHEMA_VERSION

    c.execute(f"PRAGMA user_version = {int(DB_SCHEMA_VERSION)}")  # data schema version pinned
    c.commit()


def columns() -> dict[str, list[str]]:
    with tx() as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t: [r[1] for r in c.execute(f"PRAGMA table_info({t})")] for t in tables}


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
