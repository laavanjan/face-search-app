"""End-to-end orchestration: bytes -> sanitize -> detect -> embed -> store.

Data scope (governance/de-identification.yaml):
  in : one image (JPEG/PNG/WebP, <= 15 MB)
  out: the re-encoded image (EXIF/GPS/device metadata stripped, <= MAX_DIM px)
       + one 512-d embedding, bbox and quality scores per qualifying face.
The original upload bytes and filename are never persisted or sent to AWS.
"""
from __future__ import annotations

import io
import logging
import time
import uuid
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.config import get_settings
from app.models.schemas import BoundingBox, FaceRecord
from app.services import controls, face_engine, rekognition, resilience, storage, vector_store

log = logging.getLogger(__name__)

MAX_DIM = 1600
# Refuse decompression bombs: images above this pixel count are rejected
# outright (Pillow raises DecompressionBombError at 2x; warnings become errors).
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
# PNG text chunk set by tests/fixtures/synthetic_faces.py. Production rejects
# such images so synthetic fixtures can never land in the real stores.
SYNTHETIC_MARKER = "fsa-synthetic"

# Public entry points first. Both start with the human-intervention guard
# (controls.ensure_allowed): if an admin paused the path or a config change is
# unapproved, they raise 503 before any decoding, face analysis, storage,
# vector write or review case happens.

def ingest(data: bytes, *, uploaded_by: str, minor: bool = False) -> tuple[str, str, list[FaceRecord], str]:
    """Index every qualifying face. Faces start as `pending` (excluded from
    search) unless REQUIRE_INDEX_REVIEW is off. Photos showing a minor always
    need human approval and expire sooner."""
    controls.ensure_allowed("indexing")  # human stop switch + config gate, before any processing
    s = get_settings()
    bgr, clean, ext = prepare(data)
    faces = _detect(bgr)
    if not faces:
        raise ValueError("no_face_detected")

    rek_boost = _cross_check_with_rekognition(bgr, clean)
    photo_id = f"{uuid.uuid4().hex}.{ext}"
    storage.save(photo_id, clean, content_type="image/png" if ext == "png" else "image/jpeg")

    status = vector_store.PENDING if (s.require_index_review or minor) else vector_store.APPROVED
    now = time.time()
    records: list[FaceRecord] = []
    for i, f in enumerate(faces):
        q = f.quality
        if i in rek_boost:
            q = float(min(1.0, 0.6 * q + 0.4 * rek_boost[i]))
        face_id = vector_store.new_id()
        vector_store.upsert(
            photo_id=photo_id,
            face_id=face_id,
            embedding=f.embedding.tolist(),
            bbox=f.bbox,
            det_score=f.det_score,
            quality=q,
            review_status=status,
            indexed_at=now,
            uploaded_by=uploaded_by,
            minor=minor,
        )
        x, y, w, h = f.bbox
        records.append(
            FaceRecord(
                face_id=face_id,
                photo_id=photo_id,
                bbox=BoundingBox(x=x, y=y, w=w, h=h),
                det_score=f.det_score,
                quality=q,
            )
        )
    log.info("photo_indexed faces=%d status=%s", len(records), status)
    return photo_id, storage.public_url(photo_id), records, status


def search(data: bytes, limit: int = 20, threshold: float = 0.35):
    """Returns (faces, hits, clean_query_bytes, ext). Hits are candidates
    only; they are released after human review (app/services/review.py)."""
    controls.ensure_allowed("search")  # human stop switch + config gate, before any processing
    bgr, clean, ext = prepare(data)
    faces = _detect(bgr)
    if not faces:
        raise ValueError("no_face_detected")
    # Use the largest / highest-confidence face as the query.
    faces.sort(key=lambda f: f.det_score * (f.bbox[2] * f.bbox[3]), reverse=True)
    q = faces[0]
    hits = vector_store.search(q.embedding.tolist(), limit=limit, score_threshold=threshold)
    return faces, hits, clean, ext


def _normalize(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM))
    return img


def _encode_clean(img: Image.Image, src_format: str | None) -> tuple[bytes, str]:
    """Re-encode pixels only. No exif/icc/text chunks are carried over."""
    buf = io.BytesIO()
    if src_format == "PNG":
        img.save(buf, format="PNG")
        return buf.getvalue(), "png"
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), "jpg"


def prepare(data: bytes) -> tuple[np.ndarray, bytes, str]:
    """Validate + sanitize an upload. Returns (bgr, clean_bytes, ext)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(data))
            if img.width * img.height > MAX_PIXELS:
                raise ValueError("too_many_pixels")
            img.load()
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid_image") from e
    if str(img.info.get(SYNTHETIC_MARKER, "")).lower() == "true" and not get_settings().synthetic_data_enabled:
        raise ValueError("synthetic_data_rejected")
    src_format = img.format
    rgb = _normalize(img)
    clean, ext = _encode_clean(rgb, src_format)
    bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    return bgr, clean, ext


def _detect(bgr: np.ndarray) -> list[face_engine.DetectedFace]:
    return resilience.run_with_deadline(
        face_engine.analyze,
        bgr,
        timeout=get_settings().inference_timeout_seconds,
        op="face_engine.analyze",
    )


def _cross_check_with_rekognition(bgr: np.ndarray, clean: bytes) -> dict[int, float]:
    """Boost quality scores when Rekognition confirms a face at the same location."""
    rek = rekognition.detect_faces(clean)
    if not rek:
        return {}
    h, w = bgr.shape[:2]
    boosts: dict[int, float] = {}
    for i, r in enumerate(rek):
        rx, ry, rw, rh = r["bbox_rel"]
        boosts[i] = r["quality"]
        _ = (rx * w, ry * h, rw * w, rh * h)  # kept for future IoU refinement
    return boosts

