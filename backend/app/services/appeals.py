"""Appeals / recourse (docs/oversight/appeals-and-sla.md).

Anyone - including people who appear in photos but have no account - can
file an appeal. Filing one about a specific photo immediately restricts it
(`disputed`: excluded from search and from released matches) until a human
resolves the appeal. Contact details are optional and only visible to staff
with appeals:manage: they are validated, encrypted at rest (services/crypto.py),
never written to the audit log, and wiped APPEAL_CONTACT_RETENTION_DAYS after
resolution.
"""
from __future__ import annotations

import time
import uuid

from fastapi import HTTPException

from app.config import get_settings
from app.security import Principal
from app.services import audit, crypto, db, retention, storage, vector_store

DAY = 86400
CATEGORIES = {"incorrect_match", "indexing_objection", "deletion_request", "access_request", "other"}
RESTRICTING = {"incorrect_match", "indexing_objection", "deletion_request"}
OUTCOMES = {"upheld", "partially_upheld", "rejected"}
ACTIONS = {"none", "delete_photo", "restore_photo"}

_PUBLIC_FIELDS = ("id", "created_at", "category", "status", "ack_by", "resolve_by", "outcome", "resolution", "resolved_at")


def submit(
    category: str,
    reason: str,
    photo_id: str | None,
    face_id: str | None,
    case_id: str | None,
    contact: str | None,
    submitter: Principal | None,
) -> dict:
    if category not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {sorted(CATEGORIES)}")
    s = get_settings()
    now = time.time()
    appeal_id = uuid.uuid4().hex
    restricted = False
    if photo_id and not storage.valid_photo_id(photo_id):
        photo_id = None
    if photo_id and category in RESTRICTING:
        restricted = vector_store.set_photo_status(photo_id, vector_store.DISPUTED) > 0
    with db.tx() as c:
        c.execute(
            "INSERT INTO appeals (id, created_at, category, photo_id, face_id, case_id, reason, contact, "
            "status, ack_by, resolve_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                appeal_id, now, category, photo_id, face_id, case_id, reason,
                crypto.encrypt(contact.strip().lower()) if contact else None,  # encrypted at rest
                "received", now + s.appeal_ack_days * DAY, now + s.appeal_resolution_days * DAY,
            ),
        )
    audit.record(
        submitter or Principal("anonymous", ("public",), frozenset()),
        "appeal.submit", appeal_id, category=category, restricted=restricted,
    )
    out = public_view(appeal_id)
    out["photo_restricted"] = restricted
    return out


def _row(appeal_id: str) -> dict:
    with db.tx() as c:
        r = c.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Appeal not found")
    return dict(r)


def public_view(appeal_id: str) -> dict:
    r = _row(appeal_id)
    return {k: r[k] for k in _PUBLIC_FIELDS}


def list_all(status: str | None = None, limit: int = 200) -> list[dict]:
    q, args = "SELECT * FROM appeals", []
    if status:
        q += " WHERE status = ?"
        args.append(status)
    q += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with db.tx() as c:
        rows = [dict(r) for r in c.execute(q, args).fetchall()]
    now = time.time()
    for r in rows:
        r["contact"] = crypto.decrypt(r["contact"])  # only appeals:manage reaches this
        r["overdue"] = r["status"] != "resolved" and now > r["resolve_by"]
    return rows


def acknowledge(appeal_id: str, actor: Principal) -> dict:
    r = _row(appeal_id)
    if r["status"] == "received":
        with db.tx() as c:
            c.execute("UPDATE appeals SET status='in_review' WHERE id=?", (appeal_id,))
        audit.record(actor, "appeal.acknowledge", appeal_id)
    return _row(appeal_id)


def resolve(appeal_id: str, outcome: str, resolution: str, action: str, actor: Principal) -> dict:
    if outcome not in OUTCOMES:
        raise HTTPException(422, f"outcome must be one of {sorted(OUTCOMES)}")
    if action not in ACTIONS:
        raise HTTPException(422, f"action must be one of {sorted(ACTIONS)}")
    r = _row(appeal_id)
    if r["status"] == "resolved":
        raise HTTPException(409, "Appeal already resolved")
    pid = r["photo_id"]
    if action != "none" and not pid:
        raise HTTPException(422, "This appeal does not reference a photo")
    if action == "delete_photo":
        if not actor.can("photos:delete"):
            raise HTTPException(403, "Missing permission: photos:delete")
        retention.delete_photo(pid, actor, f"appeal:{appeal_id}")
    elif action == "restore_photo":
        vector_store.set_photo_status(pid, vector_store.APPROVED)
    # action == "none": a disputed photo stays excluded from search.
    with db.tx() as c:
        c.execute(
            "UPDATE appeals SET status='resolved', outcome=?, resolution=?, resolved_by=?, resolved_at=? WHERE id=?",
            (outcome, resolution, actor.ref, time.time(), appeal_id),
        )
    audit.record(actor, "appeal.resolve", appeal_id, outcome=outcome, action=action)
    return _row(appeal_id)
