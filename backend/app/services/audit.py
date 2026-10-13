"""Append-only audit trail for oversight-relevant actions.

Records actor, roles, action and an opaque target. Free-text `detail` must not
carry image bytes, embeddings or contact details.
"""
from __future__ import annotations

import json
import time
from typing import Any

from app.security import Principal
from app.services import db

SYSTEM = Principal("system", ("system",), frozenset())


def record(actor: Principal, action: str, target: str | None = None, /, **detail: Any) -> None:
    with db.tx() as c:
        c.execute(
            "INSERT INTO audit_log (ts, actor, roles, action, target, detail) VALUES (?,?,?,?,?,?)",
            (
                time.time(),
                actor.name,
                "+".join(actor.roles),
                action,
                target,
                json.dumps(detail, default=str) if detail else None,
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
        out.append(d)
    return out
