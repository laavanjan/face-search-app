"""Deletion + retention enforcement (governance/data-retention-policy.yaml).

`delete_photo` is the single deletion path. It is used by
DELETE /photos/{id}, appeal resolution, index-review rejection and the TTL
sweep, so request-driven and expiry-driven deletion behave identically:
stored image + every face vector + any pending review candidates go together.
"""
from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.security import Principal
from app.services import audit, db, storage, vector_store

log = logging.getLogger(__name__)

DAY = 86400


def delete_photo(photo_id: str, actor: Principal, reason: str) -> dict:
    vectors = vector_store.delete_by_photo_id(photo_id)
    stored = storage.delete(photo_id) if storage.valid_photo_id(photo_id) else False
    with db.tx() as c:
        cands = c.execute(
            "DELETE FROM review_candidates WHERE photo_id = ?", (photo_id,)
        ).rowcount
    if vectors or stored:
        audit.record(actor, "photo.delete", photo_id, decision="delete", reason=reason,
                     evidence={"vectors": vectors, "file_deleted": stored, "candidates_removed": cands})
    return {"photo_id": photo_id, "vectors_deleted": vectors, "file_deleted": stored, "candidates_removed": cands}


def purge_expired(now: float | None = None) -> dict:
    s = get_settings()
    now = now or time.time()
    photos = vector_store.expired_photo_ids(now - s.photo_retention_days * DAY)
    for pid in photos:
        delete_photo(pid, audit.SYSTEM, "retention_ttl")
    with db.tx() as c:
        cases = c.execute(
            "DELETE FROM review_cases WHERE created_at < ?",
            (now - s.review_case_retention_days * DAY,),
        ).rowcount
        # Closed cases keep their decision record but not the query image.
        c.execute(
            "UPDATE review_cases SET query_image = NULL WHERE status NOT IN ('pending_review', 'escalated') "
            "AND query_image IS NOT NULL"
        )
        # Contact details are only needed to send the decision.
        c.execute(
            "UPDATE appeals SET contact = NULL WHERE status = 'resolved' AND contact IS NOT NULL "
            "AND resolved_at < ?",
            (now - s.appeal_contact_retention_days * DAY,),
        )
        appeals = c.execute(
            "DELETE FROM appeals WHERE status = 'resolved' AND resolved_at < ?",
            (now - s.appeal_retention_days * DAY,),
        ).rowcount
        # Oldest-first, one row at a time: the append-only trigger only allows
        # expiring the head, which keeps the remaining hash chain contiguous.
        audit_rows = 0
        cutoff = now - s.audit_log_retention_days * DAY
        while True:
            head = c.execute("SELECT id, ts FROM audit_log ORDER BY id LIMIT 1").fetchone()
            if not head or head["ts"] >= cutoff:
                break
            c.execute("DELETE FROM audit_log WHERE id = ?", (head["id"],))
            audit_rows += 1
    result = {
        "photos_deleted": len(photos),
        "review_cases_deleted": cases,
        "appeals_deleted": appeals,
        "audit_rows_deleted": audit_rows,
    }
    if any(result.values()):
        audit.record(audit.SYSTEM, "retention.sweep", None, **result)
        log.info("retention_sweep %s", result)
    return result
