"""Edge cases, abuse and adversarial inputs (SAFE-01, SAFE-02).

Each adversarial case maps to a scenario in governance/red-team-report.yaml.
"""
import io
from unittest.mock import patch

import pytest
from PIL import Image

from app.config import get_settings
from app.services import pipeline
from tests.conftest import ADMIN, OPERATOR, REVIEWER, VIEWER
from tests.fixtures.synthetic_faces import synthetic_face, synthetic_png


def _post(client, path, data: bytes, ctype="image/png", headers=OPERATOR, **form):
    form.setdefault("consent", "true")
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(901)]):
        return client.post(path, files={"file": ("x", data, ctype)}, data=form, headers=headers)


# --- malformed and boundary inputs -----------------------------------------------


@pytest.mark.parametrize(
    "data,ctype,code",
    [
        (b"", "image/png", 400),                    # empty
        (b"not an image at all", "image/png", 400),  # spoofed content type
        (b"GIF89a....", "image/gif", 415),            # unsupported type
        (b"%PDF-1.4", "application/pdf", 415),
    ],
)
def test_upload_rejects_malformed(client, data, ctype, code):
    assert _post(client, "/upload", data, ctype).status_code == code


def test_upload_rejects_oversize(client):
    assert _post(client, "/upload", b"\x89PNG" + b"0" * (15 * 1024 * 1024 + 1)).status_code == 413


def test_decompression_bomb_rejected():
    # 8000 x 8000 1-bit PNG: tiny file, 64 MP when decoded.
    buf = io.BytesIO()
    Image.new("1", (8000, 8000)).save(buf, format="PNG")
    assert len(buf.getvalue()) < 2_000_000
    with pytest.raises(ValueError, match="invalid_image"):
        pipeline.prepare(buf.getvalue())


@pytest.mark.parametrize("form", [{"limit": "0"}, {"limit": "100000"}, {"threshold": "1.5"}, {"threshold": "-1"}, {"limit": "abc"}])
def test_search_parameter_bounds(client, form):
    assert _post(client, "/search", synthetic_png(), **form).status_code == 422


def test_no_face_returns_422_not_500(client):
    with patch("app.services.face_engine.analyze", return_value=[]):
        r = client.post("/upload", files={"file": ("x", synthetic_png(), "image/png")}, data={"consent": "true"}, headers=OPERATOR)
    assert r.status_code == 422


def test_backend_outage_fails_closed_with_503(client):
    from qdrant_client.http.exceptions import ResponseHandlingException

    with patch("app.services.vector_store.search", side_effect=ResponseHandlingException(ConnectionError("down"))):
        r = _post(client, "/search", synthetic_png())
    assert r.status_code == 503


@pytest.mark.parametrize(
    "path",
    [
        "/review/cases/1'%20OR%20'1'='1",
        "/review/cases/" + "a" * 33,
        "/review/cases/" + "z" * 32,
        "/photos/" + "a" * 32 + ".exe",
        "/appeals/../../etc",
    ],
)
def test_injection_like_ids_rejected(client, path):
    # Authorised caller, so the request reaches validation rather than 403.
    headers = REVIEWER if path.startswith("/review") else VIEWER
    assert client.get(path, headers=headers).status_code in (404, 422)


@pytest.mark.parametrize("reason", ["", "ab", "x" * 1001])
def test_decision_reason_bounds(client, reason):
    r = client.post("/admin/controls", json={"search_paused": False, "reason": reason}, headers=ADMIN)
    assert r.status_code == 422


def test_unicode_reason_accepted(client):
    r = client.post("/admin/controls", json={"search_paused": False, "reason": "Überprüfung ✓ 検査"}, headers=ADMIN)
    assert r.status_code == 200


# --- abuse cases (red team) -----------------------------------------------------


def test_api_key_bruteforce_locked_out(client):
    codes = [client.get("/gallery", headers={"Authorization": f"Bearer guess-{i}"}).status_code for i in range(25)]
    assert codes[0] == 401 and 429 in codes
    # Even the right key is refused while locked out.
    assert client.get("/gallery", headers=VIEWER).status_code == 429


def test_appeal_flood_rate_limited(client):
    body = {"category": "other", "reason": "Flooding attempt number one."}
    codes = [client.post("/appeals", json=body).status_code for _ in range(8)]
    assert codes[:5] == [201] * 5 and codes[-1] == 429


def test_threshold_cannot_be_lowered_by_caller(client):
    r = _post(client, "/search", synthetic_png(), threshold="0.0")
    assert r.json()["threshold_applied"] == get_settings().search_min_threshold


def test_consent_bypass_rejected(client):
    assert _post(client, "/upload", synthetic_png(), consent="false").status_code == 422


def test_synthetic_fixture_injection_rejected_in_production(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "synthetic_data_enabled", False)
    assert _post(client, "/upload", synthetic_png()).status_code == 422


def test_contact_field_injection_rejected(client):
    r = client.post("/appeals", json={"category": "other", "reason": "Ordinary reason text.", "contact": "<script>alert(1)</script>"})
    assert r.status_code == 422


def test_privilege_escalation_attempts(client):
    assert client.post("/admin/config/approve", json={"change_id": "CHG-X", "reason": "sneaky"}, headers=REVIEWER).status_code == 403
    assert client.delete("/photos/" + "a" * 32 + ".jpg?reason=sneaky", headers=OPERATOR).status_code == 403
    assert client.post("/admin/controls", json={"search_paused": True, "reason": "sneaky"}, headers=VIEWER).status_code == 403


def test_forged_trace_header_is_not_trusted(client):
    r = client.get("/health", headers={"X-Request-ID": "bad id\r\nInjected: 1"})
    assert r.headers["X-Request-ID"] != "bad id\r\nInjected: 1"
    assert len(r.headers["X-Request-ID"]) == 32
