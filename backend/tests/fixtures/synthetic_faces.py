"""Synthetic test data - the only data the test suite uses.

Images: flat-colour Pillow canvases (no faces, no people). PNGs carry the
`fsa-synthetic=true` text chunk; the pipeline rejects that marker unless
SYNTHETIC_DATA_ENABLED=true, so fixtures cannot be ingested by a production
deployment.
Embeddings: seeded NumPy standard-normal 512-d vectors, L2-normalised.
Random unit vectors in 512-d are near-orthogonal (cosine ~ 0 +/- 0.05), so
different seeds model "different people" and equal seeds "the same person".

These fixtures exercise pipeline mechanics only. They carry no demographic,
pose, lighting or camera variation and must never be used to claim accuracy
or fairness (governance/synthetic-data-bias-assessment.yaml).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, PngImagePlugin

from app.services import face_engine
from app.services.pipeline import SYNTHETIC_MARKER

DIM = 512


def synthetic_png(w: int = 200, h: int = 200, color=(200, 180, 160)) -> bytes:
    img = Image.new("RGB", (w, h), color=color)
    meta = PngImagePlugin.PngInfo()
    meta.add_text(SYNTHETIC_MARKER, "true")
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()


def synthetic_jpeg_with_exif(w: int = 200, h: int = 200) -> bytes:
    """JPEG carrying camera EXIF, to prove the pipeline strips metadata."""
    img = Image.new("RGB", (w, h), color=(90, 120, 150))
    exif = Image.Exif()
    exif[0x010F] = "SyntheticCam"  # Make
    exif[0x0110] = "Model-X"  # Model
    exif[0x9286] = "user comment"  # UserComment-like free text
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def synthetic_embedding(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def synthetic_face(seed: int, bbox=(10, 10, 100, 100)) -> face_engine.DetectedFace:
    return face_engine.DetectedFace(
        bbox=bbox, det_score=0.98, embedding=synthetic_embedding(seed), quality=0.9
    )
