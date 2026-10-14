"""Provenance marking for system outputs (TRAN-08).

This service generates no images, so pixel watermarking does not apply. Its
outputs are match decisions and indexing results. Each one carries a signed
provenance block so anyone holding the deployment key can check where a result
came from and that it was not altered:

  generator, api_version, model, threshold, config_fingerprint,
  trace_id (request), subject (case/photo id), human_reviewed, generated_at,
  signature = HMAC-SHA256 over the canonical JSON of the block + payload digest
              (sub-key "provenance", services/crypto.py).

Photos served from /photos/{id} carry an X-Content-Provenance header saying
they are user uploads, re-encoded with metadata stripped - not AI-generated.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json

from app.config import get_settings
from app.services import crypto
from app.tracing import current_trace_id
from app.version import APP_VERSION as API_VERSION

GENERATOR = "face-search-api"
PHOTO_HEADER = "origin=user-upload; processing=re-encoded,metadata-stripped; ai-generated=false"


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()


def stamp(payload: dict, subject: str, human_reviewed: bool) -> dict:
    s = get_settings()
    block = {
        "generator": GENERATOR,
        "api_version": API_VERSION,
        "model": s.face_model_name,
        "threshold": s.search_min_threshold,
        "config_fingerprint": s.governance_fingerprint()[:16],
        "trace_id": current_trace_id(),
        "subject": subject,
        "human_reviewed": human_reviewed,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "payload_sha256": hashlib.sha256(_canonical(payload)).hexdigest(),
    }
    block["signature"] = crypto.mac("provenance", _canonical(block))
    return block


def verify(payload: dict, block: dict) -> bool:
    b = dict(block)
    sig = b.pop("signature", "")
    if b.get("payload_sha256") != hashlib.sha256(_canonical(payload)).hexdigest():
        return False
    return hmac.compare_digest(sig, crypto.mac("provenance", _canonical(b)))
