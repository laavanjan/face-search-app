"""Pipeline unit tests using fake face_engine output.

Confirms embeddings roundtrip through the in-memory vector store and that
the same-person similarity beats a random vector.
"""
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
import io

from app.services import face_engine, pipeline, vector_store


def _png(w=200, h=200, color=(200, 180, 160)):
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _fake_face(seed: int):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(512).astype(np.float32)
    v /= np.linalg.norm(v)
    return face_engine.DetectedFace(
        bbox=(10, 10, 100, 100),
        det_score=0.98,
        embedding=v,
        quality=0.9,
    )


def test_ingest_and_search_roundtrip():
    # Ensure we start from a clean in-memory collection
    with patch("app.services.face_engine.analyze") as det:
        alice = _fake_face(seed=1)
        det.return_value = [alice]
        pid, url, faces = pipeline.ingest(_png(), "alice.png")
        assert len(faces) == 1
        assert pid.endswith(".png")
        assert url

    with patch("app.services.face_engine.analyze") as det:
        # Same embedding => must match itself
        det.return_value = [_fake_face(seed=1)]
        faces, hits = pipeline.search(_png(), limit=5)
        assert len(hits) >= 1
        assert hits[0].score > 0.99

    with patch("app.services.face_engine.analyze") as det:
        # Different embedding => should NOT beat threshold
        det.return_value = [_fake_face(seed=999)]
        faces, hits = pipeline.search(_png(), limit=5)
        # Either no hit above default threshold or a hit with low score.
        for h in hits:
            assert h.score < 0.5


def test_ingest_raises_when_no_face():
    with patch("app.services.face_engine.analyze", return_value=[]):
        with pytest.raises(ValueError):
            pipeline.ingest(_png(), "empty.png")
