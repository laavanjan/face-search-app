"""Append-only, hash-chained decision log / audit trail (DOC-04, DOC-07, TRAN-05, TRAN-06).

audit_log schema: ts, actor (pseudonym), roles, action, target, detail,
trace_id (request that caused it), rationale (structured JSON),
prev_hash + row_hash (SHA-256 chain: row_hash = H(prev_hash, row fields)).

Integrity: the table is append-only (SQLite triggers refuse UPDATE and any
DELETE except expiring the oldest row), and verify_chain() recomputes every
hash so any edited, inserted or removed row is detected. Exposed at
GET /admin/audit/verify and checked at start-up.

Every decision path writes a row: upload, search case creation, index
approve/reject, candidate approve/reject/reopen, manual match, case close,
appeal submit/resolve, pause/resume, config approval, deletion, retention.

`rationale` is structured so a decision can be reconstructed without the UI:
  inputs              what the decision was based on (scores, face ids, counts, settings)
  output              {decision, action, target} - what was decided, about what
  decision            the outcome (e.g. "approve", "pending_review", "stopped")
  reason              the human's stated reason (required for human decisions)
  model / threshold   model and similarity floor in force
  config_fingerprint  hash of the governance-sensitive settings in force
Free text must not carry image bytes, embeddings or contact details.
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.config import get_settings
from app.security import Principal
from app.services import db
from app.tracing import current_trace_id

SYSTEM = Principal("system", ("system",), frozenset())
RATIONALE_FIELDS = ("inputs", "output", "decision", "reason", "model", "threshold", "config_fingerprint")


def _rationale(action: str, target: str | None, decision: str, reason: str | None, evidence: dict | None) -> str:
    s = get_settings()
    return json.dumps(
        {
            "inputs": evidence or {},
            "output": {"decision": decision, "action": action, "target": target},
            "decision": decision,
            "reason": reason,
            "model": s.face_model_name,
            "threshold": s.search_min_threshold,
            "config_fingerprint": s.governance_fingerprint()[:16],
        },
        default=str,
    )


def record(
    actor: Principal,
    action: str,
    target: str | None = None,
    /,
    *,
    decision: str | None = None,
    reason: str | None = None,
    evidence: dict | None = None,
    **detail: Any,
) -> None:
    """Write one audit row. Pass `decision` (+ reason/evidence) for any decision
    so the structured rationale is recorded."""
    if reason is not None:
        detail["reason"] = reason
    row = {
        "ts": time.time(),
        "actor": actor.ref,
        "roles": "+".join(actor.roles),
        "action": action,
        "target": target,
        "detail": json.dumps(detail, default=str) if detail else None,
        "trace_id": current_trace_id(),
        "rationale": _rationale(action, target, decision, reason, evidence) if decision else None,
    }
    with db.tx() as c:  # db lock held: chain head cannot change underneath us
        last = c.execute("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = last["row_hash"] if last else db.GENESIS
        c.execute(
            "INSERT INTO audit_log (ts, actor, roles, action, target, detail, trace_id, rationale, prev_hash, row_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (*[row[f] for f in db.AUDIT_HASHED_FIELDS], prev, db.row_digest(prev, row)),
        )


def verify_chain() -> dict:
    """Recompute the hash chain. ok=False names the first row that fails."""
    with db.tx() as c:
        rows = c.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    expected = rows[0]["prev_hash"] if rows else db.GENESIS  # head may have been expired
    for r in rows:
        d = dict(r)
        if d["prev_hash"] != expected or d["row_hash"] != db.row_digest(d["prev_hash"], d):
            return {"ok": False, "rows": len(rows), "first_bad_id": d["id"]}
        expected = d["row_hash"]
    return {"ok": True, "rows": len(rows), "head": expected}


def recent(limit: int = 200, action: str | None = None) -> list[dict]:
    q = "SELECT * FROM audit_log"
    args: list[Any] = []
    if action:
        q += " WHERE action = ?"
        args.append(action)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with db.tx() as c:
        rows = c.execute(q, args).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["detail"] = json.loads(d["detail"]) if d["detail"] else {}
        d["rationale"] = json.loads(d["rationale"]) if d.get("rationale") else None
        out.append(d)
    return out
