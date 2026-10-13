"""Append-only decision log / audit trail (TRAN-05, TRAN-06).

audit_log schema: ts, actor (pseudonym), roles, action, target, detail,
trace_id (request that caused it), rationale (structured JSON).

Every decision path writes a row: upload, search case creation, index
approve/reject, candidate approve/reject/reopen, manual match, case close,
appeal submit/resolve, pause/resume, config approval, deletion, retention.

`rationale` is structured so a decision can be reconstructed without the UI:
  decision            the outcome (e.g. "approve", "pending_review", "stopped")
  reason              the human's stated reason (required for human decisions)
  evidence            inputs the decision was based on (scores, counts, ids)
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
RATIONALE_FIELDS = ("decision", "reason", "evidence", "model", "threshold", "config_fingerprint")


def _rationale(decision: str, reason: str | None, evidence: dict | None) -> str:
    s = get_settings()
    return json.dumps(
        {
            "decision": decision,
            "reason": reason,
            "evidence": evidence or {},
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
    with db.tx() as c:
        c.execute(
            "INSERT INTO audit_log (ts, actor, roles, action, target, detail, trace_id, rationale) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                time.time(),
                actor.ref,
                "+".join(actor.roles),
                action,
                target,
                json.dumps(detail, default=str) if detail else None,
                current_trace_id(),
                _rationale(decision, reason, evidence) if decision else None,
            ),
        )


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
