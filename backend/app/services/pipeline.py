"""End-to-end orchestration: bytes -> detect -> embed -> store."""
from __future__ import annotations

import io
import logging
import uuid

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.models.schemas import BoundingBox, FaceRecord
from app.services import face_engine, rekognition, storage, vector_store

log = logging.getLogger(__name__)

MAX_DIM = 1600


def _decode(data: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM))
    arr = np.array(img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _cross_check_with_rekognition(bgr: np.ndarray, data: bytes) -> dict[int, float]:
    """Boost quality scores when Rekognition confirms a face at the same location."""
    rek = rekognition.detect_faces(data)
    if not rek:
        return {}
    h, w = bgr.shape[:2]
    boosts: dict[int, float] = {}
    for i, r in enumerate(rek):
        rx, ry, rw, rh = r["bbox_rel"]
        boosts[i] = r["quality"]
        _ = (rx * w, ry * h, rw * w, rh * h)  # kept for future IoU refinement
    return boosts


def ingest(data: bytes, filename: str) -> tuple[str, str, list[FaceRecord]]:
    bgr = _decode(data)
    faces = face_engine.analyze(bgr)
    if not faces:
        raise ValueError("no_face_detected")

    rek_boost = _cross_check_with_rekognition(bgr, data)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    photo_id = f"{uuid.uuid4().hex}.{ext}"
    storage.save(photo_id, data, content_type=f"image/{ext}")

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
            filename=filename,
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
    return photo_id, storage.public_url(photo_id), records


def search(data: bytes, limit: int = 20):
    bgr = _decode(data)
    faces = face_engine.analyze(bgr)
    if not faces:
        raise ValueError("no_face_detected")
    # Use the largest / highest-confidence face as the query.
    faces.sort(key=lambda f: f.det_score * (f.bbox[2] * f.bbox[3]), reverse=True)
    q = faces[0]
    hits = vector_store.search(q.embedding.tolist(), limit=limit)
    return faces, hits
