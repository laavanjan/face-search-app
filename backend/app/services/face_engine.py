"""InsightFace detector + ArcFace embedder.

Loaded lazily so the app can start (and tests can import) without the model
being present on disk. First call triggers a ~200MB download via insightface's
model zoo into ~/.insightface.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import numpy as np

from app.config import get_settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_app = None


@dataclass
class DetectedFace:
    bbox: tuple[int, int, int, int]  # x, y, w, h
    det_score: float
    embedding: np.ndarray  # (512,) L2-normalized
    quality: float


def _get_app():
    global _app
    if _app is not None:
        return _app
    with _lock:
        if _app is None:
            from insightface.app import FaceAnalysis

            # Model identity comes from settings so the evaluated artefact is
            # recorded and any change trips the config-approval gate.
            s = get_settings()
            log.info("Loading InsightFace %s...", s.face_model_name)
            # Only detection + recognition: the pack also ships age/gender and
            # landmark models, which this service must not run (data minimisation).
            fa = FaceAnalysis(
                name=s.face_model_name,
                allowed_modules=["detection", "recognition"],
                providers=["CPUExecutionProvider"],
            )
            fa.prepare(ctx_id=-1, det_size=(s.face_det_size, s.face_det_size))
            _app = fa
            log.info("InsightFace ready.")
    return _app


def _l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def analyze(image_bgr: np.ndarray) -> list[DetectedFace]:
    """Detect + embed every face. Returns [] when none found."""
    s = get_settings()
    faces = _get_app().get(image_bgr)
    out: list[DetectedFace] = []
    for f in faces:
        if float(f.det_score) < s.min_det_score:
            continue
        x1, y1, x2, y2 = [int(v) for v in f.bbox]
        w, h = x2 - x1, y2 - y1
        if min(w, h) < s.min_face_size:
            continue
        emb = _l2(np.asarray(f.normed_embedding, dtype=np.float32))
        # quality proxy: geometric mean of det_score and normalized size
        img_h, img_w = image_bgr.shape[:2]
        rel = (w * h) / float(img_w * img_h)
        quality = float(np.sqrt(min(1.0, f.det_score) * min(1.0, rel * 20)))
        out.append(
            DetectedFace(
                bbox=(max(0, x1), max(0, y1), w, h),
                det_score=float(f.det_score),
                embedding=emb,
                quality=quality,
            )
        )
    return out


def is_ready() -> bool:
    return _app is not None
