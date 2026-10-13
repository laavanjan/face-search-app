"""End-to-end tests for the access-control, human-oversight, recourse and
privacy controls (see docs/README.md for the control -> test mapping)."""
import logging
import time
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.logging_setup import RedactingFilter, redact
from app.main import app
from app.security import _key_entries
from app.services import db, pipeline, resilience, retention, storage, vector_store
from tests.conftest import ADMIN, OPERATOR, REVIEWER, SAM, VIEWER
from tests.fixtures.synthetic_faces import synthetic_face, synthetic_png


def _upload(client, seed: int, headers=OPERATOR, consent=True):
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(seed)]):
        return client.post(
            "/upload",
            files={"file": ("p.png", synthetic_png(), "image/png")},
            data={"consent": str(consent).lower()},
            headers=headers,
        )


def _search(client, seed: int, threshold=0.35, headers=OPERATOR):
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(seed)]):
        return client.post(
            "/search",
            files={"file": ("q.png", synthetic_png(), "image/png")},
            data={"threshold": str(threshold), "consent": "true"},
            headers=headers,
        )


def _approved_photo(client, seed: int) -> str:
    pid = _upload(client, seed).json()["photo_id"]
    r = client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "consent on file"}, headers=REVIEWER)
    assert r.status_code == 200, r.text
    return pid


# --- PRIV-05: access control -----------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/upload"),
        ("post", "/search"),
        ("get", "/gallery"),
        ("get", "/photos/" + "a" * 32 + ".jpg"),
        ("delete", "/photos/" + "a" * 32 + ".jpg?reason=test"),
        ("get", "/review/photos"),
        ("get", "/review/cases"),
        ("get", "/appeals"),
        ("get", "/admin/controls"),
        ("get", "/admin/audit"),
    ],
)
def test_protected_endpoints_deny_anonymous(client, method, path):
    assert getattr(client, method)(path).status_code == 401
    bad = {"Authorization": "Bearer nope"}
    assert getattr(client, method)(path, headers=bad).status_code == 401


def test_least_privilege(client):
    assert client.post("/upload", headers=VIEWER, files={"file": ("p.png", b"x", "image/png")}).status_code == 403
    assert client.get("/review/photos", headers=OPERATOR).status_code == 403
    assert client.get("/admin/controls", headers=REVIEWER).status_code == 403
    assert client.delete("/photos/" + "a" * 32 + ".jpg?reason=x12", headers=REVIEWER).status_code == 403
    assert client.get("/admin/audit", headers=OPERATOR).status_code == 403
    me = client.get("/auth/me", headers=OPERATOR).json()
    assert me["roles"] == ["operator"] and "photos:delete" not in me["permissions"]


def test_photo_id_path_traversal_rejected(client):
    # Rejected by path validation before any handler or storage code runs.
    assert client.get("/photos/..%2F..%2Fetc%2Fpasswd", headers=VIEWER).status_code in (404, 422)
    assert client.get("/photos/not-a-photo.jpg", headers=VIEWER).status_code == 422


# --- PRIV-02: lawful basis ---------------------------------------------------------


def test_upload_requires_consent_and_is_recorded(client):
    assert _upload(client, 101, consent=False).status_code == 422
    assert _upload(client, 101).status_code == 200
    log = client.get("/admin/audit?action=lawful_basis.asserted", headers=ADMIN).json()["items"]
    assert log[0]["detail"]["basis"] == "consent"
    assert log[0]["detail"]["notice_version"] == get_settings().privacy_notice_version


# --- HUMO-06 / HUMO-02: indexing gate ----------------------------------------------


def test_upload_is_pending_until_reviewer_approves(client):
    r = _upload(client, 202)
    assert r.json()["review_status"] == "pending"
    pid = r.json()["photo_id"]
    assert _search(client, 202).json()["candidate_count"] == 0

    pending = client.get("/review/photos", headers=REVIEWER).json()["items"]
    assert pid in {p["photo_id"] for p in pending}
    assert client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "ok ok"}, headers=OPERATOR).status_code == 403
    client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "consent verified"}, headers=REVIEWER)
    assert _search(client, 202).json()["candidate_count"] == 1


def test_reject_at_index_review_deletes_photo(client):
    pid = _upload(client, 203).json()["photo_id"]
    client.post(f"/review/photos/{pid}", json={"decision": "reject", "reason": "no consent"}, headers=REVIEWER)
    assert not storage.exists(pid)
    assert vector_store.faces_for_photo(pid) == []


def test_separation_of_duties(client):
    pid = _upload(client, 204, headers=SAM).json()["photo_id"]
    r = client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "self"}, headers=SAM)
    assert r.status_code == 403


# --- HUMO-07 / HUMO-02 / HUMO-06: disclosure gate --------------------------------


def test_search_results_released_only_after_review(client):
    pid = _approved_photo(client, 301)
    r = _search(client, 301, threshold=0.0).json()
    assert r["status"] == "pending_review"
    assert r["matches"] == []
    assert r["threshold_applied"] == get_settings().search_min_threshold  # cannot go below floor
    case = r["case_id"]

    # Requester sees nothing while pending.
    assert client.get(f"/search/cases/{case}", headers=OPERATOR).json()["matches"] == []

    full = client.get(f"/review/cases/{case}", headers=REVIEWER).json()
    face_id = full["candidates"][0]["face_id"]
    assert client.get(f"/review/cases/{case}/query-image", headers=REVIEWER).status_code == 200

    # Cannot complete with undecided candidates.
    assert client.post(f"/review/cases/{case}/close", json={"outcome": "completed", "reason": "done"}, headers=REVIEWER).status_code == 409
    client.post(f"/review/cases/{case}/candidates/{face_id}", json={"decision": "approve", "reason": "same person"}, headers=REVIEWER)
    client.post(f"/review/cases/{case}/close", json={"outcome": "completed", "reason": "verified"}, headers=REVIEWER)

    out = client.get(f"/search/cases/{case}", headers=OPERATOR).json()
    assert out["status"] == "completed"
    assert [m["photo_id"] for m in out["matches"]] == [pid]
    # Stored and returned as a pseudonym, never the reviewer's account name.
    assert out["matches"][0]["reviewed_by"] == client.get("/auth/me", headers=REVIEWER).json()["ref"]
    assert out["matches"][0]["reviewed_by"] != "rita"
    # Query image is dropped once the case closes.
    assert client.get(f"/review/cases/{case}/query-image", headers=REVIEWER).status_code == 404


def test_stop_prevents_release(client):
    _approved_photo(client, 302)
    case = _search(client, 302).json()["case_id"]
    face_id = client.get(f"/review/cases/{case}", headers=REVIEWER).json()["candidates"][0]["face_id"]
    client.post(f"/review/cases/{case}/candidates/{face_id}", json={"decision": "approve", "reason": "looks right"}, headers=REVIEWER)
    r = client.post(f"/review/cases/{case}/close", json={"outcome": "stopped", "reason": "purpose unclear"}, headers=REVIEWER)
    assert r.json()["status"] == "stopped"
    assert client.get(f"/search/cases/{case}", headers=OPERATOR).json()["matches"] == []
    assert client.post(f"/review/cases/{case}/candidates/{face_id}", json={"decision": "approve", "reason": "x again"}, headers=REVIEWER).status_code == 409
    # Explicit human reopen is the only way back.
    assert client.post(f"/review/cases/{case}/reopen", json={"reason": "clarified"}, headers=REVIEWER).json()["status"] == "pending_review"


def test_human_takeover_manual_match(client):
    pid = _approved_photo(client, 303)
    case = _search(client, 304).json()  # different person -> no model candidates
    assert case["status"] == "no_match"
    case_id = case["case_id"]
    client.post(f"/review/cases/{case_id}/reopen", json={"reason": "operator escalated"}, headers=REVIEWER)
    client.post(f"/review/cases/{case_id}/manual-match", json={"photo_id": pid, "reason": "identified manually"}, headers=REVIEWER)
    client.post(f"/review/cases/{case_id}/close", json={"outcome": "completed", "reason": "done"}, headers=REVIEWER)
    m = client.get(f"/search/cases/{case_id}", headers=OPERATOR).json()["matches"]
    assert m[0]["source"] == "human" and m[0]["score"] is None


def test_other_operator_cannot_read_case(client):
    _approved_photo(client, 305)
    case = _search(client, 305, headers=SAM).json()["case_id"]
    assert client.get(f"/search/cases/{case}", headers=OPERATOR).status_code == 403


# --- HUMO-02: stop switch + config approval gate ----------------------------------


def test_admin_can_pause_and_resume(client):
    client.post("/admin/controls", json={"search_paused": True, "reason": "incident P1"}, headers=ADMIN)
    assert _search(client, 1).status_code == 503
    assert client.get("/health").json()["search_paused"] is True
    client.post("/admin/controls", json={"search_paused": False, "reason": "resolved"}, headers=ADMIN)
    assert _search(client, 1).status_code == 200


def test_config_change_requires_approval(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "min_det_score", 0.2)
    assert _upload(client, 401).status_code == 503
    status = client.get("/admin/controls", headers=ADMIN).json()["config"]
    assert status["pending_diff"]["min_det_score"] == {"approved": 0.5, "running": 0.2}
    client.post("/admin/config/approve", json={"change_id": "CHG-TEST", "reason": "evaluated"}, headers=ADMIN)
    assert _upload(client, 401).status_code == 200


# --- HUMO-03: appeals -------------------------------------------------------------


def test_appeal_restricts_photo_until_resolved(client):
    pid = _approved_photo(client, 501)
    r = client.post(
        "/appeals",
        json={"category": "incorrect_match", "reason": "That is not me in this photo.", "photo_id": pid, "contact": "me@example.org"},
    )
    assert r.status_code == 201
    appeal = r.json()
    assert appeal["photo_restricted"] is True
    assert appeal["resolve_by"] > appeal["created_at"]
    assert _search(client, 501).json()["candidate_count"] == 0  # restricted

    # Status lookup is subject-scoped: needs the token issued at submission.
    assert client.get(f"/appeals/{appeal['id']}").status_code == 404
    assert client.get(f"/appeals/{appeal['id']}", headers={"X-Appeal-Token": "wrong"}).status_code == 404
    public = client.get(f"/appeals/{appeal['id']}", headers={"X-Appeal-Token": appeal["access_token"]}).json()
    assert "contact" not in public and public["status"] == "received"

    queue = client.get("/appeals", headers=REVIEWER).json()["items"]
    assert any(a["id"] == appeal["id"] and a["contact"] == "me@example.org" for a in queue)

    client.post(f"/appeals/{appeal['id']}/resolve", json={"outcome": "rejected", "resolution": "Verified match", "action": "restore_photo"}, headers=REVIEWER)
    assert _search(client, 501).json()["candidate_count"] == 1


def test_deletion_appeal_needs_delete_permission(client):
    pid = _approved_photo(client, 502)
    a = client.post("/appeals", json={"category": "deletion_request", "reason": "Please erase my photo.", "photo_id": pid}).json()
    body = {"outcome": "upheld", "resolution": "Erased", "action": "delete_photo"}
    assert client.post(f"/appeals/{a['id']}/resolve", json=body, headers=REVIEWER).status_code == 403
    assert client.post(f"/appeals/{a['id']}/resolve", json=body, headers=ADMIN).status_code == 200
    assert not storage.exists(pid)


# --- PRIV-04: deletion + retention --------------------------------------------------


def test_delete_endpoint_removes_file_and_vectors(client):
    pid = _approved_photo(client, 601)
    r = client.delete(f"/photos/{pid}?reason=subject%20request", headers=ADMIN)
    assert r.status_code == 200 and r.json()["vectors_deleted"] == 1
    assert not storage.exists(pid)
    assert vector_store.faces_for_photo(pid) == []
    assert client.delete(f"/photos/{pid}?reason=again", headers=ADMIN).status_code == 404


def test_retention_ttl_purges_expired_photos(client):
    pid = _upload(client, 602).json()["photo_id"]
    ttl = get_settings().photo_retention_days * 86400
    assert retention.purge_expired()["photos_deleted"] == 0 or storage.exists(pid)
    assert pid not in vector_store.expired_photo_ids(time.time() - ttl)
    future = time.time() + ttl + 86400
    result = retention.purge_expired(now=future)
    assert result["photos_deleted"] >= 1
    assert not storage.exists(pid)


# --- PRIV-01: log redaction ---------------------------------------------------------


def test_logs_redact_personal_data():
    msg = "GET /photos/0123456789abcdef0123456789abcdef.jpg from 10.1.2.3 user a.b@x.org file holiday-alice.jpeg Bearer abc.def"
    out = redact(msg)
    for leaked in ("0123456789abcdef", "10.1.2.3", "a.b@x.org", "holiday-alice", "abc.def"):
        assert leaked not in out
    rec = logging.LogRecord("t", logging.INFO, "f", 1, '%s "%s %s"', ("10.0.0.9:5000", "GET", "/photos/" + "f" * 32 + ".png"), None)
    RedactingFilter().filter(rec)
    assert isinstance(rec.args, tuple) and "f" * 32 not in rec.getMessage()
    # Format strings that look like URLs must still format (uvicorn startup line).
    rec = logging.LogRecord("t", logging.INFO, "f", 1, "running on %s://%s:%d", ("http", "127.0.0.1", 8000), None)
    RedactingFilter().filter(rec)
    assert rec.getMessage() == "running on http://127.0.0.x:8000"


# --- HUMO-04: deadlines + retries ---------------------------------------------------


def test_inference_deadline_returns_504(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "inference_timeout_seconds", 0.05)
    with patch("app.services.face_engine.analyze", side_effect=lambda *_: time.sleep(0.5) or []):
        r = client.post("/upload", files={"file": ("p.png", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR)
    assert r.status_code == 504


def test_retry_only_transient(monkeypatch):
    monkeypatch.setattr(resilience.time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("reset")
        return "ok"

    assert resilience.retry(flaky, op="t", attempts=3) == "ok"
    calls["n"] = 0

    def bad():
        calls["n"] += 1
        raise ValueError("no_face_detected")

    with pytest.raises(ValueError):
        resilience.retry(bad, op="t", attempts=3)
    assert calls["n"] == 1


# --- PRIV-05: auth is the default on every route ---------------------------------

PUBLIC_ROUTES = {
    ("GET", "/"), ("GET", "/health"), ("GET", "/policy"),
    ("POST", "/appeals"), ("GET", "/appeals/{appeal_id}"),
}


def test_every_route_requires_auth_except_allowlist(client):
    checked = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        if not hasattr(route, "methods") or path.startswith(("/docs", "/openapi", "/redoc")):
            continue
        for method in route.methods - {"HEAD", "OPTIONS"}:
            if (method, path) in PUBLIC_ROUTES:
                continue
            url = path.replace("{photo_id}", "a" * 32 + ".jpg").replace("{case_id}", "x").replace(
                "{face_id}", "y").replace("{appeal_id}", "z")
            r = client.request(method, url)
            assert r.status_code == 401, (method, path, r.status_code)
            checked += 1
    assert checked >= 20


def test_role_bundles_need_allowlist_and_production_needs_hashed_tokens():
    assert _key_entries("x:admin+reviewer:t", "", "development") == ()
    assert len(_key_entries("x:operator+reviewer:t", "operator+reviewer", "development")) == 1
    assert _key_entries("x:viewer:raw-token", "", "production") == ()
    assert len(_key_entries("x:viewer:sha256:" + "0" * 64, "", "production")) == 1


# --- PRIV-01: no names or plaintext contacts in stored records -------------------


def _db_dump() -> str:
    with db.tx() as c:
        return "\n".join(c.iterdump())


def test_records_store_pseudonyms_not_names(client):
    pid = _approved_photo(client, 701)
    _search(client, 701)
    dump = _db_dump()
    for name in ("olivia", "rita", "adam"):
        assert name not in dump
    assert all(not f["uploaded_by"].startswith("olivia") for f in vector_store.faces_for_photo(pid))


def test_appeal_contact_encrypted_and_expires(client):
    a = client.post("/appeals", json={"category": "other", "reason": "Please call me back about this.", "contact": "Person@Example.org"}).json()
    assert "person@example.org" not in _db_dump()
    queue = client.get("/appeals", headers=REVIEWER).json()["items"]
    assert any(x["id"] == a["id"] and x["contact"] == "person@example.org" for x in queue)
    assert client.post("/appeals", json={"category": "other", "reason": "Bad contact value here.", "contact": "not a contact"}).status_code == 422
    client.post(f"/appeals/{a['id']}/resolve", json={"outcome": "rejected", "resolution": "No action"}, headers=REVIEWER)
    retention.purge_expired(now=time.time() + 31 * 86400)
    with db.tx() as c:
        row = c.execute("SELECT contact FROM appeals WHERE id = ?", (a["id"],)).fetchone()
    assert row is None or row["contact"] is None


# --- HUMO-02: intervention enforced inside the pipeline itself -------------------


def test_pipeline_refuses_when_paused(client):
    client.post("/admin/controls", json={"indexing_paused": True, "search_paused": True, "reason": "drill"}, headers=ADMIN)
    try:
        with patch("app.services.face_engine.analyze") as det:
            with pytest.raises(Exception) as e1:
                pipeline.ingest(synthetic_png(), uploaded_by="x")
            with pytest.raises(Exception) as e2:
                pipeline.search(synthetic_png())
            det.assert_not_called()
        assert getattr(e1.value, "status_code", None) == 503
        assert getattr(e2.value, "status_code", None) == 503
    finally:
        client.post("/admin/controls", json={"indexing_paused": False, "search_paused": False, "reason": "drill over"}, headers=ADMIN)
