r"""Human review gates (governance/human-approval-gates.yaml).

Two high-risk paths, both fail closed:

1. Indexing   upload -> faces stored as `pending` -> reviewer approves -> searchable
                                               \-> reviewer rejects  -> photo deleted
2. Disclosure search -> case `pending_review` with model candidates
              -> reviewer approves / rejects each candidate, may add a manual
                 match (human takeover), stop, escalate or close as no-match
              -> only on `completed` are approved matches released to the requester.

A reviewer cannot decide their own upload or search unless ALLOW_SELF_REVIEW.
"""
from __future__ import annotations

import json
import time
import uuid

from fastapi import HTTPException

from app.config import get_settings
from app.security import Principal
from app.services import audit, db, explain, retention, vector_store

PENDING_REVIEW = "pending_review"
ESCALATED = "escalated"
COMPLETED = "completed"
NO_MATCH = "no_match"
STOPPED = "stopped"
OPEN_STATES = {PENDING_REVIEW, ESCALATED}


def _no_self_review(owner: str | None, actor: Principal) -> None:
    if owner and owner == actor.ref and not get_settings().allow_self_review:
        raise HTTPException(403, "Separation of duties: a second person must review this.")


# --- 1. indexing gate ----------------------------------------------------------


def _face_evidence(faces: list[dict]) -> dict:
    return {
        "faces": [
            {"face_id": f["face_id"], "det_score": f.get("det_score"), "quality": f.get("quality"), "bbox": f.get("bbox")}
            for f in faces
        ],
        "uploaded_by": faces[0].get("uploaded_by") if faces else None,
    }


def pending_photos(limit: int = 100) -> list[dict]:
    return vector_store.photos(limit=limit, status=vector_store.PENDING)


def decide_photo(photo_id: str, decision: str, actor: Principal, reason: str) -> dict:
    faces = vector_store.faces_for_photo(photo_id)
    if not faces:
        raise HTTPException(404, "Photo not found in index")
    _no_self_review(faces[0].get("uploaded_by"), actor)
    if decision == "approve":
        vector_store.set_photo_status(photo_id, vector_store.APPROVED)
        audit.record(actor, "index.approve", photo_id, decision="approve", reason=reason, evidence=_face_evidence(faces))
        return {"photo_id": photo_id, "review_status": vector_store.APPROVED}
    if decision == "reject":
        audit.record(actor, "index.reject", photo_id, decision="reject", reason=reason, evidence=_face_evidence(faces))
        retention.delete_photo(photo_id, actor, f"index_rejected: {reason}")
        return {"photo_id": photo_id, "review_status": "rejected_deleted"}
    raise HTTPException(422, "decision must be approve or reject")


# --- 2. disclosure gate --------------------------------------------------------


def create_case(
    requester: Principal, threshold: float, query_faces: int, hits, query_image: bytes, ext: str,
    purpose: str = "self",
) -> dict:
    case_id = uuid.uuid4().hex
    now = time.time()
    # Every search goes to a human, even with zero candidates. Closing empty
    # searches automatically would tell the requester "this person is not in
    # the library" before review - a membership-inference leak (SEC-07).
    status = PENDING_REVIEW
    with db.tx() as c:
        c.execute(
            "INSERT INTO review_cases (id, created_at, requested_by, status, threshold, query_faces, "
            "query_image, query_media_type, closed_by, closed_at, close_reason) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                case_id,
                now,
                requester.ref,
                status,
                threshold,
                query_faces,
                query_image,
                "image/png" if ext == "png" else "image/jpeg",
                None,
                None,
                None,
            ),
        )
        for h in hits:
            pl = h.payload or {}
            c.execute(
                "INSERT INTO review_candidates (case_id, face_id, photo_id, score, bbox, source, decision) "
                "VALUES (?,?,?,?,?,?,?)",
                (case_id, str(h.id), pl["photo_id"], float(h.score), json.dumps(pl.get("bbox") or [0, 0, 0, 0]), "model", "pending"),
            )
    audit.record(
        requester, "search.case_created", case_id, decision=status,
        evidence={
            "threshold_applied": threshold,
            "purpose": purpose,
            "query_faces": query_faces,
            "candidates": [{"face_id": str(h.id), "photo_id": (h.payload or {}).get("photo_id"), "score": round(float(h.score), 4)} for h in hits],
        },
    )
    return {"case_id": case_id, "status": status, "candidate_count": len(hits)}


def _case_row(case_id: str) -> dict:
    with db.tx() as c:
        r = c.execute(
            "SELECT id, created_at, requested_by, status, threshold, query_faces, closed_by, closed_at, "
            "close_reason, query_image IS NOT NULL AS has_query_image FROM review_cases WHERE id = ?",
            (case_id,),
        ).fetchone()
    if not r:
        raise HTTPException(404, "Case not found")
    return dict(r)


def _candidates(case_id: str) -> list[dict]:
    with db.tx() as c:
        rows = c.execute(
            "SELECT * FROM review_candidates WHERE case_id = ? ORDER BY score DESC NULLS LAST", (case_id,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["bbox"] = json.loads(d["bbox"])
        out.append(d)
    return out


def get_case(case_id: str) -> dict:
    case = _case_row(case_id)
    case["candidates"] = _candidates(case_id)
    return case


def list_cases(status: str | None = None, limit: int = 100) -> list[dict]:
    q = (
        "SELECT c.id, c.created_at, c.requested_by, c.status, c.threshold, c.query_faces, "
        "(SELECT COUNT(*) FROM review_candidates k WHERE k.case_id = c.id) AS candidates, "
        "(SELECT COUNT(*) FROM review_candidates k WHERE k.case_id = c.id AND k.decision = 'pending') AS undecided "
        "FROM review_cases c"
    )
    args: list = []
    if status:
        q += " WHERE c.status = ?"
        args.append(status)
    q += " ORDER BY c.created_at DESC LIMIT ?"
    args.append(limit)
    with db.tx() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def query_image(case_id: str) -> tuple[bytes, str]:
    with db.tx() as c:
        r = c.execute("SELECT query_image, query_media_type FROM review_cases WHERE id = ?", (case_id,)).fetchone()
    if not r or r["query_image"] is None:
        raise HTTPException(404, "Query image not retained")
    return r["query_image"], r["query_media_type"]


def released_matches(case_id: str, viewer: Principal) -> dict:
    """What the requester may see: approved matches, and only once completed."""
    case = _case_row(case_id)
    if case["requested_by"] != viewer.ref and not viewer.can("review:decide"):
        raise HTTPException(403, "Not your case")
    matches = []
    if case["status"] == COMPLETED:
        for k in _candidates(case_id):
            if k["decision"] != "approve":
                continue
            faces = vector_store.faces_for_photo(k["photo_id"])
            if not faces or any(f.get("review_status") == vector_store.DISPUTED for f in faces):
                continue  # deleted or under appeal since approval
            matches.append(k)
    return {
        "case_id": case_id,
        "status": case["status"],
        "query_faces": case["query_faces"],
        "threshold_applied": case["threshold"],
        "matches": matches,
    }


def _require_open(case: dict) -> None:
    if case["status"] not in OPEN_STATES:
        raise HTTPException(409, f"Case is {case['status']}; reopen it first")


def decide_candidate(
    case_id: str, face_id: str, decision: str, actor: Principal, reason: str, ack_low_confidence: bool = False
) -> dict:
    case = _case_row(case_id)
    _require_open(case)
    _no_self_review(case["requested_by"], actor)
    new = {"approve": "approve", "reject": "reject", "reopen": "pending"}.get(decision)
    if not new:
        raise HTTPException(422, "decision must be approve, reject or reopen")
    if decision == "approve":
        # Automation-bias guard (ACC-03): approving a match the model itself is
        # unsure about needs an explicit acknowledgement, not a reflex click.
        k = next((c for c in _candidates(case_id) if c["face_id"] == face_id), None)
        if k and explain.confidence_band(k["score"], case["threshold"]) == "low" and not ack_low_confidence:
            raise HTTPException(
                422,
                "Low-confidence candidate: confirm you compared the faces yourself "
                "(acknowledge_low_confidence=true) before approving.",
            )
    with db.tx() as c:
        n = c.execute(
            "UPDATE review_candidates SET decision=?, decided_by=?, decided_at=?, reason=? "
            "WHERE case_id=? AND face_id=?",
            (new, actor.ref, time.time(), reason, case_id, face_id),
        ).rowcount
    if not n:
        raise HTTPException(404, "Candidate not found")
    k = next((c for c in _candidates(case_id) if c["face_id"] == face_id), {})
    audit.record(actor, f"search.candidate.{decision}", case_id, decision=decision, reason=reason,
                 evidence={"face_id": face_id, "photo_id": k.get("photo_id"), "score": k.get("score"), "source": k.get("source")})
    return get_case(case_id)


def add_manual_match(case_id: str, photo_id: str, actor: Principal, reason: str) -> dict:
    """Human takeover: confirm a photo the model did not propose."""
    case = _case_row(case_id)
    _require_open(case)
    _no_self_review(case["requested_by"], actor)
    faces = vector_store.faces_for_photo(photo_id)
    if not faces:
        raise HTTPException(404, "Photo not found in index")
    with db.tx() as c:
        c.execute(
            "INSERT OR REPLACE INTO review_candidates (case_id, face_id, photo_id, score, bbox, source, "
            "decision, decided_by, decided_at, reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (case_id, f"manual:{photo_id}", photo_id, None, json.dumps([0, 0, 0, 0]), "human",
             "approve", actor.ref, time.time(), reason),
        )
    audit.record(actor, "search.manual_match", case_id, decision="approve", reason=reason,
                 evidence={"photo_id": photo_id, "source": "human"})
    return get_case(case_id)


def close_case(case_id: str, outcome: str, actor: Principal, reason: str) -> dict:
    case = _case_row(case_id)
    _require_open(case)
    _no_self_review(case["requested_by"], actor)
    if outcome not in {COMPLETED, NO_MATCH, STOPPED, ESCALATED}:
        raise HTTPException(422, "outcome must be completed, no_match, stopped or escalated")
    with db.tx() as c:
        if outcome == COMPLETED:
            undecided = c.execute(
                "SELECT COUNT(*) FROM review_candidates WHERE case_id=? AND decision='pending'", (case_id,)
            ).fetchone()[0]
            if undecided:
                raise HTTPException(409, f"{undecided} candidate(s) still undecided")
        if outcome == NO_MATCH:
            c.execute(
                "UPDATE review_candidates SET decision='reject', decided_by=?, decided_at=?, reason=? "
                "WHERE case_id=? AND decision != 'reject'",
                (actor.ref, time.time(), reason, case_id),
            )
        terminal = outcome != ESCALATED
        c.execute(
            "UPDATE review_cases SET status=?, closed_by=?, closed_at=?, close_reason=?"
            + (", query_image=NULL" if terminal else "")
            + " WHERE id=?",
            (outcome, actor.ref, time.time(), reason, case_id),
        )
    final = _candidates(case_id)
    audit.record(actor, f"search.case.{outcome}", case_id, decision=outcome, reason=reason,
                 evidence={"approved": [k["face_id"] for k in final if k["decision"] == "approve"],
                           "rejected": [k["face_id"] for k in final if k["decision"] == "reject"]})
    return get_case(case_id)


def reopen_case(case_id: str, actor: Principal, reason: str) -> dict:
    case = _case_row(case_id)
    if case["status"] == PENDING_REVIEW:
        raise HTTPException(409, "Case is already open")
    with db.tx() as c:
        c.execute(
            "UPDATE review_cases SET status=?, closed_by=NULL, closed_at=NULL, close_reason=NULL WHERE id=?",
            (PENDING_REVIEW, case_id),
        )
    audit.record(actor, "search.case.reopen", case_id, decision="reopen", reason=reason,
                 evidence={"previous_status": case["status"]})
    return get_case(case_id)
