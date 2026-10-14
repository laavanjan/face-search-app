"""Human intervention controls: pause/resume switches and the config-change gate.

- `indexing_paused` / `search_paused` are set by an admin (system:control) and
  checked on every upload / search before any biometric processing happens.
- The config gate fingerprints governance-sensitive settings
  (Settings.governance_snapshot). If the running config differs from the last
  approved baseline, indexing and search fail closed until an admin approves
  the change with a change-record id (governance/change-management.yaml).
"""
from __future__ import annotations

import json
import time

from fastapi import HTTPException

from app.config import get_settings
from app.security import Principal
from app.services import audit, db

KINDS = ("indexing", "search")


def _flag(key: str) -> dict | None:
    with db.tx() as c:
        r = c.execute("SELECT * FROM controls WHERE key = ?", (key,)).fetchone()
    return dict(r) if r else None


def is_paused(kind: str) -> bool:
    r = _flag(f"{kind}_paused")
    return bool(r and r["value"] == "1")


def set_paused(kind: str, paused: bool, actor: Principal, reason: str) -> None:
    if kind not in KINDS:
        raise ValueError(kind)
    with db.tx() as c:
        c.execute(
            "INSERT INTO controls (key, value, updated_by, updated_at, reason) VALUES (?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_by=excluded.updated_by, "
            "updated_at=excluded.updated_at, reason=excluded.reason",
            (f"{kind}_paused", "1" if paused else "0", actor.ref, time.time(), reason),
        )
    audit.record(actor, f"control.{kind}.{'pause' if paused else 'resume'}", None,
                 decision="pause" if paused else "resume", reason=reason, evidence={"kind": kind})


# --- configuration change gate -------------------------------------------------


def _snapshot() -> tuple[str, dict]:
    s = get_settings()
    return s.governance_fingerprint(), s.governance_snapshot()


def _approved_baselines() -> list[dict]:
    with db.tx() as c:
        rows = c.execute("SELECT * FROM config_baselines ORDER BY approved_at DESC").fetchall()
    return [dict(r) for r in rows]


def bootstrap_baseline() -> None:
    """First start: record the running config as the initial baseline."""
    if _approved_baselines():
        return
    fp, snap = _snapshot()
    with db.tx() as c:
        c.execute(
            "INSERT INTO config_baselines VALUES (?,?,?,?,?)",
            (fp, json.dumps(snap), "bootstrap", "system", time.time()),
        )
    audit.record(audit.SYSTEM, "config.baseline.bootstrap", fp[:12])


def config_status() -> dict:
    fp, snap = _snapshot()
    approved = _approved_baselines()
    ok = any(b["fingerprint"] == fp for b in approved)
    last = approved[0] if approved else None
    diff = {}
    if last and not ok:
        prev = json.loads(last["snapshot"])
        diff = {k: {"approved": prev.get(k), "running": v} for k, v in snap.items() if prev.get(k) != v}
    return {
        "fingerprint": fp,
        "approved": ok,
        "last_approved_change_id": last["change_id"] if last else None,
        "pending_diff": diff,
    }


def approve_config(actor: Principal, change_id: str, reason: str) -> dict:
    fp, snap = _snapshot()
    with db.tx() as c:
        c.execute(
            "INSERT OR REPLACE INTO config_baselines VALUES (?,?,?,?,?)",
            (fp, json.dumps(snap), change_id, actor.ref, time.time()),
        )
    audit.record(actor, "config.approve", fp[:12], decision="approve", reason=reason,
                 evidence={"change_id": change_id, "fingerprint": fp, "settings": snap})
    return config_status()


def ensure_allowed(kind: str) -> None:
    """Fail closed before any biometric processing on a critical path.

    Called by every critical path: routes/upload.py and routes/search.py on
    entry, and again inside pipeline.ingest() / pipeline.search() so no caller
    can reach face analysis, storage, vectors or review cases while paused."""
    bootstrap_baseline()
    if not config_status()["approved"]:
        raise HTTPException(
            503, "Configuration change awaiting governance approval; processing is paused."
        )
    if is_paused(kind):
        raise HTTPException(503, f"{kind.capitalize()} is paused by an operator.")


def summary() -> dict:
    from app.services import carbon

    return {
        "compute_budget": carbon.usage(),
        "indexing_paused": is_paused("indexing"),
        "search_paused": is_paused("search"),
        "config": config_status(),
    }
