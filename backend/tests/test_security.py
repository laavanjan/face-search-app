"""Security and traceability controls (SEC-01..07, DOC-04, DOC-05, DOC-07)."""
import json
import re
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import get_settings
from app.main import app
from app.services import audit, db, vector_store
from app.version import APP_VERSION, MANIFEST
from tests.conftest import ADMIN, OPERATOR, REVIEWER, VIEWER
from tests.fixtures.synthetic_faces import synthetic_face, synthetic_png

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


# --- DOC-07: append-only, tamper-evident audit log --------------------------------


def _write_some(n=3):
    for i in range(n):
        audit.record(audit.SYSTEM, "test.event", f"t{i}", decision="noop", evidence={"i": i})


def test_audit_log_is_append_only():
    _write_some()
    with db.tx() as c:
        last = c.execute("SELECT MAX(id) FROM audit_log").fetchone()[0]
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        with db.tx() as c:
            c.execute("UPDATE audit_log SET action = 'forged' WHERE id = ?", (last,))
    with pytest.raises(sqlite3.DatabaseError, match="oldest-first"):
        with db.tx() as c:
            c.execute("DELETE FROM audit_log WHERE id = ?", (last,))


def test_hash_chain_detects_tampering(client):
    _write_some()
    assert audit.verify_chain()["ok"]
    assert client.get("/admin/audit/verify", headers=ADMIN).json()["ok"] is True
    with db.tx() as c:
        row = c.execute("SELECT id, action FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        c.execute("DROP TRIGGER audit_log_no_update")  # attacker with raw DB access
        c.execute("UPDATE audit_log SET action = 'forged' WHERE id = ?", (row["id"],))
    try:
        bad = audit.verify_chain()
        assert bad["ok"] is False and bad["first_bad_id"] == row["id"]
    finally:
        with db.tx() as c:
            c.execute("UPDATE audit_log SET action = ? WHERE id = ?", (row["action"], row["id"]))
            c.executescript(db._TRIGGERS)
    assert audit.verify_chain()["ok"]


def test_expiring_head_keeps_chain_valid():
    from app.services import retention

    _write_some()
    with db.tx() as c:
        n_before = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    retention.purge_expired(now=__import__("time").time() + (get_settings().audit_log_retention_days + 1) * 86400)
    assert audit.verify_chain()["ok"]
    with db.tx() as c:
        assert c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] < n_before


# --- DOC-05: pinned versions --------------------------------------------------------


def test_version_manifest_matches_code():
    s = get_settings()
    reqs = (BACKEND / "requirements.txt").read_text()
    assert app.version == APP_VERSION
    assert json.loads((ROOT / "frontend" / "package.json").read_text())["version"] == MANIFEST["code"]["frontend_version"]
    assert MANIFEST["model"]["package"] in reqs and MANIFEST["model"]["runtime"] in reqs
    assert s.face_model_name == MANIFEST["model"]["name"]
    assert s.face_det_size == MANIFEST["model"]["det_size"]
    assert vector_store.DIM == MANIFEST["model"]["embedding_dim"]
    assert f"## {APP_VERSION}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    with db.tx() as c:
        assert c.execute("PRAGMA user_version").fetchone()[0] == MANIFEST["data"]["governance_db_schema_version"]
    assert MANIFEST["prompts"]["version"] == "none"


def test_version_endpoint_requires_auth(client):
    assert client.get("/version").status_code == 401
    assert client.get("/version", headers=VIEWER).json()["code"]["version"] == APP_VERSION


# --- SEC-01: deny by default, no hard-coded secrets --------------------------------


def test_unrouted_paths_are_denied_not_disclosed(client):
    assert client.get("/internal/debug").status_code == 401
    assert client.get("/internal/debug", headers=VIEWER).status_code == 404


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),                                  # AWS access key id
    re.compile(r"(?i)(secret|password|api_key|token)\s*=\s*['\"][^'\"]{12,}['\"]"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def test_no_hardcoded_secrets_in_app_code():
    for path in (BACKEND / "app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pat in SECRET_PATTERNS:
            assert not pat.search(text), f"possible secret in {path}"


# --- SEC-02: no LLM / agent paths ---------------------------------------------------

LLM_PACKAGES = re.compile(r"(?im)^\s*(openai|anthropic|langchain\S*|llama[-_]?index|transformers|litellm|cohere|google-generativeai)\b")


def test_no_llm_or_agent_dependencies():
    for f in ("requirements.txt", "requirements-dev.txt"):
        assert not LLM_PACKAGES.search((BACKEND / f).read_text()), f
    pkg = json.loads((ROOT / "frontend" / "package.json").read_text())
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert not [d for d in deps if re.match(r"(openai|@anthropic-ai|langchain|ai$)", d)]
    for path in (BACKEND / "app").rglob("*.py"):
        assert not re.search(r"(?m)^\s*(import|from)\s+(openai|anthropic|langchain)", path.read_text(encoding="utf-8")), path


# --- SEC-07: embeddings never leave the server --------------------------------------


def _has_embedding(obj) -> bool:
    if isinstance(obj, list):
        if len(obj) >= 128 and all(isinstance(x, float) for x in obj):
            return True
        return any(_has_embedding(x) for x in obj)
    if isinstance(obj, dict):
        return any(_has_embedding(v) for v in obj.values())
    return False


def test_api_never_returns_embeddings(client):
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(1301)]):
        up = client.post("/upload", files={"file": ("p", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR)
        pid = up.json()["photo_id"]
        client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "ok ok"}, headers=REVIEWER)
        case = client.post("/search", files={"file": ("q", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()["case_id"]
    responses = [
        up.json(),
        client.get("/gallery", headers=VIEWER).json(),
        client.get(f"/review/cases/{case}", headers=REVIEWER).json(),
        client.get(f"/review/cases/{case}/explain", headers=REVIEWER).json(),
        client.get("/review/photos", headers=REVIEWER).json(),
        client.get("/admin/audit", headers=ADMIN).json(),
    ]
    for r in responses:
        assert not _has_embedding(r)


# --- SEC-04: rate limiting + abuse reporting ----------------------------------------


def test_global_rate_limit_middleware(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 5)
    codes = [client.get("/health").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[-1] == 429


def test_abuse_report_endpoint(client):
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(1302)]):
        pid = client.post("/upload", files={"file": ("p", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()["photo_id"]
    r = client.post("/abuse-reports", json={"kind": "non_consensual_search", "description": "Someone searched for me without asking.", "photo_id": pid})
    assert r.status_code == 201 and r.json()["photo_restricted"] is True
    queue = client.get("/appeals", headers=REVIEWER).json()["items"]
    assert any(a["id"] == r.json()["id"] and a["category"] == "abuse_report" for a in queue)
    assert client.post("/abuse-reports", json={"kind": "bogus", "description": "x" * 20}).status_code == 422


def test_search_does_not_leak_membership(client):
    """A requester cannot tell 'in the library' from 'not in the library'
    before a reviewer acts (SEC-07, system-level membership inference)."""
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(1401)]):
        pid = client.post("/upload", files={"file": ("p", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()["photo_id"]
        client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "ok ok"}, headers=REVIEWER)
        present = client.post("/search", files={"file": ("q", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(1402)]):
        absent = client.post("/search", files={"file": ("q", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()
    strip = lambda r: {k: v for k, v in r.items() if k != "case_id"}  # noqa: E731
    assert strip(present) == strip(absent)
    for r in (present, absent):
        follow = client.get(f"/search/cases/{r['case_id']}", headers=OPERATOR).json()
        assert follow["status"] == "pending_review" and follow["matches"] == []
