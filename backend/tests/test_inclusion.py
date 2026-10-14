"""Accessibility, human factors and societal controls (ACC-01..08, SOC-01..08)."""
import json
import re
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app.config import get_settings
from app.services import face_engine, retention, storage, vector_store
from tests.conftest import OPERATOR, REVIEWER
from tests.fixtures.synthetic_faces import synthetic_embedding, synthetic_face, synthetic_png

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def _upload(client, seed, **form):
    form.setdefault("consent", "true")
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(seed)]):
        return client.post("/upload", files={"file": ("p", synthetic_png(), "image/png")}, data=form, headers=OPERATOR)


# --- ACC-05: vulnerable users -------------------------------------------------------


def test_minors_need_guardian_consent_and_human_review(client, monkeypatch):
    assert _upload(client, 2001, minors_present="true").status_code == 422
    child = _upload(client, 2003, minors_present="true", guardian_consent="true").json()
    assert child["review_status"] == "pending"
    assert vector_store.faces_for_photo(child["photo_id"])[0]["minor"] is True
    # Even where indexing review is switched off, children's photos still go to a human.
    # (Changing that setting trips the config gate, so bypass it for this unit check.)
    from app.services import pipeline

    monkeypatch.setattr(get_settings(), "require_index_review", False)
    with patch("app.services.controls.ensure_allowed"),          patch("app.services.face_engine.analyze", return_value=[synthetic_face(2002)]):
        *_, adult_status = pipeline.ingest(synthetic_png(), uploaded_by="x")
        *_, child_status = pipeline.ingest(synthetic_png(), uploaded_by="x", minor=True)
    assert (adult_status, child_status) == ("approved", "pending")


def test_minor_photos_expire_sooner():
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(2004)]):
        from app.services import pipeline

        adult, *_ = pipeline.ingest(synthetic_png(), uploaded_by="x")
        child, *_ = pipeline.ingest(synthetic_png(), uploaded_by="x", minor=True)
    import time

    s = get_settings()
    retention.purge_expired(now=time.time() + (s.minor_photo_retention_days + 1) * 86400)
    assert not storage.exists(child)
    assert storage.exists(adult)


# --- ACC-03: over-trust, automation bias, workflow misuse -----------------------------


def _face_with_similarity(seed: int, cos: float) -> face_engine.DetectedFace:
    base = synthetic_embedding(seed)
    other = synthetic_embedding(seed + 7777)
    other = other - other.dot(base) * base
    other /= np.linalg.norm(other)
    v = cos * base + np.sqrt(1 - cos * cos) * other
    return face_engine.DetectedFace(bbox=(10, 10, 100, 100), det_score=0.9, embedding=v.astype(np.float32), quality=0.8)


def test_search_requires_a_permitted_purpose(client):
    files = {"file": ("q", synthetic_png(), "image/png")}
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(2101)]):
        assert client.post("/search", files=files, data={"consent": "true"}, headers=OPERATOR).status_code == 422
        assert client.post("/search", files=files, data={"consent": "true", "purpose": "surveillance"}, headers=OPERATOR).status_code == 422


def test_low_confidence_approval_needs_acknowledgement(client):
    pid = _upload(client, 2102).json()["photo_id"]
    client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "consent ok"}, headers=REVIEWER)
    with patch("app.services.face_engine.analyze", return_value=[_face_with_similarity(2102, 0.40)]):
        case = client.post("/search", files={"file": ("q", synthetic_png(), "image/png")}, data={"consent": "true", "purpose": "self"}, headers=OPERATOR).json()["case_id"]
    cand = client.get(f"/review/cases/{case}", headers=REVIEWER).json()["candidates"][0]
    assert 0.35 <= cand["score"] < 0.45  # low band
    url = f"/review/cases/{case}/candidates/{cand['face_id']}"
    assert client.post(url, json={"decision": "approve", "reason": "looks alike"}, headers=REVIEWER).status_code == 422
    r = client.post(url, json={"decision": "approve", "reason": "compared side by side", "acknowledge_low_confidence": True}, headers=REVIEWER)
    assert r.status_code == 200


# --- ACC-06 / ACC-08: human alternative + accessible support channel ------------------


def test_support_channel_and_human_alternative(client):
    r = client.post("/support", json={"topic": "human_assistance", "message": "Please search the photos for me.", "preferred_format": "large_print", "language": "es"})
    assert r.status_code == 201 and r.json()["access_token"]
    queue = client.get("/appeals", headers=REVIEWER).json()["items"]
    item = next(a for a in queue if a["id"] == r.json()["id"])
    assert item["category"] == "support_request" and "human_assistance" in item["reason"] and "large_print" in item["reason"]
    assert client.post("/support", json={"topic": "nope", "message": "hello there"}).status_code == 422


# --- SOC-07: public disclosure --------------------------------------------------------


def test_transparency_report_is_public_and_suppresses_small_counts(client):
    r = client.get("/transparency-report")
    assert r.status_code == 200
    body = r.json()
    assert body["small_counts_suppressed_below"] == 5
    for k in ("searches_requested", "photos_deleted", "matches_approved_by_humans"):
        assert body[k] == 0 or body[k] == "<5" or body[k] >= 5
    assert "abuse" in body["how_to_report_harm"]


# --- SOC-03: compute budget -----------------------------------------------------------


def test_compute_budget_blocks_processing_when_spent(client, monkeypatch):
    from app.services import carbon

    monkeypatch.setattr(get_settings(), "inference_cpu_seconds_per_day", 1.0)
    carbon.charge(2.0)
    assert _upload(client, 2201).status_code == 503
    assert carbon.usage()["inference_seconds_used"] >= 2.0


# --- ACC-07: no coercive or pre-ticked consent; ACC-01: languages complete -----------


def test_no_pre_ticked_consent_in_ui():
    for f in list((FRONTEND / "app").rglob("*.tsx")) + list((FRONTEND / "components").rglob("*.tsx")):
        src = f.read_text(encoding="utf-8")
        assert "defaultChecked" not in src, f
        assert not re.search(r"checked=\{true\}", src), f
        assert not re.search(r"useState\(true\)", src), f"{f}: state that could pre-tick a box"
    assert 'useState<"" | "self" | "consenting_person">("")' in (FRONTEND / "app/search/page.tsx").read_text(encoding="utf-8")


def test_every_language_has_every_string():
    en = json.loads((FRONTEND / "locales/en.json").read_text(encoding="utf-8"))
    for f in (FRONTEND / "locales").glob("*.json"):
        other = json.loads(f.read_text(encoding="utf-8"))
        assert set(other) == set(en), f"{f.name} missing {set(en) - set(other)}"
