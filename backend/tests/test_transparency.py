"""Tracing, decision rationale, explanations, provenance and data inventory
(TRAN-02, TRAN-03, TRAN-05, TRAN-06, TRAN-08, PRIV-01)."""
from pathlib import Path
from unittest.mock import patch

import yaml

from app.services import audit, db, provenance
from tests.conftest import ADMIN, OPERATOR, REVIEWER
from tests.fixtures.synthetic_faces import synthetic_face, synthetic_png

ROOT = Path(__file__).resolve().parents[2]


def _approved_completed_case(client, seed: int) -> str:
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(seed)]):
        pid = client.post("/upload", files={"file": ("p", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()["photo_id"]
        client.post(f"/review/photos/{pid}", json={"decision": "approve", "reason": "consent ok"}, headers=REVIEWER)
        case = client.post("/search", files={"file": ("q", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR).json()["case_id"]
    face = client.get(f"/review/cases/{case}", headers=REVIEWER).json()["candidates"][0]["face_id"]
    client.post(f"/review/cases/{case}/candidates/{face}", json={"decision": "approve", "reason": "same person"}, headers=REVIEWER)
    client.post(f"/review/cases/{case}/close", json={"outcome": "completed", "reason": "verified"}, headers=REVIEWER)
    return case


def test_every_request_gets_a_trace_id(client):
    r = client.get("/health")
    assert len(r.headers["X-Request-ID"]) == 32
    assert client.get("/health", headers={"X-Request-ID": "abc12345-trace"}).headers["X-Request-ID"] == "abc12345-trace"


def test_decisions_logged_with_trace_and_structured_rationale(client):
    case = _approved_completed_case(client, 1101)
    rows = [r for r in audit.recent(500) if r["target"] == case]
    actions = {r["action"] for r in rows}
    assert {"search.case_created", "search.candidate.approve", "search.case.completed"} <= actions
    for r in rows:
        assert r["trace_id"]
        assert set(audit.RATIONALE_FIELDS) <= set(r["rationale"])
    created = next(r for r in rows if r["action"] == "search.case_created")
    assert created["rationale"]["inputs"]["candidates"][0]["score"] > 0.99  # inputs recorded
    assert created["rationale"]["output"] == {"decision": "pending_review", "action": "search.case_created", "target": case}


def test_explanations_and_confidence_bands(client):
    case = _approved_completed_case(client, 1102)
    m = client.get(f"/search/cases/{case}", headers=OPERATOR).json()
    assert m["matches"][0]["confidence_band"] == "high" and m["limitations"]
    e = client.get(f"/search/cases/{case}/explain", headers=OPERATOR).json()["explanations"][0]
    assert e["margin"] > 0 and e["factors"] and e["caveats"]
    assert client.get(f"/review/cases/{case}/explain", headers=REVIEWER).status_code == 200


def test_outputs_carry_verifiable_provenance(client):
    case = _approved_completed_case(client, 1103)
    r = client.get(f"/search/cases/{case}", headers=OPERATOR).json()
    block = r["provenance"]
    body = {"case_id": case, "status": r["status"], "matches": r["matches"]}
    assert block["human_reviewed"] is True and block["model"] == "buffalo_l"
    assert provenance.verify(body, block)
    tampered = {**body, "matches": []}
    assert not provenance.verify(tampered, block)
    pid = r["matches"][0]["photo_id"]
    assert "ai-generated=false" in client.get(f"/photos/{pid}", headers=OPERATOR).headers["X-Content-Provenance"]


def test_schema_matches_data_inventory():
    inv = yaml.safe_load((ROOT / "governance" / "data-inventory.yaml").read_text(encoding="utf-8"))["sqlite"]
    actual = db.columns()
    for table, cols in actual.items():
        assert table in inv, f"table {table} missing from governance/data-inventory.yaml"
        undocumented = set(cols) - set(inv[table])
        assert not undocumented, f"{table}: undocumented columns {undocumented}"
    for table, cols in inv.items():
        assert set(cols) <= set(actual.get(table, [])), f"inventory lists columns not in schema: {table}"


def test_policy_states_privacy_guarantee(client):
    assert "No k-anonymity" in client.get("/policy").json()["privacy_guarantee"]
