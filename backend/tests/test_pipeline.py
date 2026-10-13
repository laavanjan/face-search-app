"""Pipeline unit tests using synthetic face_engine output.

Confirms embeddings roundtrip through the in-memory vector store, that the
same-person similarity beats a random vector, and that only human-approved
faces are searchable.
"""
import io
from unittest.mock import patch

import pytest
from PIL import Image

from app.services import pipeline, storage, vector_store
from tests.fixtures.synthetic_faces import synthetic_face, synthetic_jpeg_with_exif, synthetic_png


def test_ingest_and_search_roundtrip():
    with patch("app.services.face_engine.analyze") as det:
        det.return_value = [synthetic_face(seed=1)]
        pid, url, faces, status = pipeline.ingest(synthetic_png(), uploaded_by="olivia")
        assert len(faces) == 1
        assert pid.endswith(".png")
        assert url == f"/photos/{pid}"
        assert status == vector_store.PENDING

    with patch("app.services.face_engine.analyze") as det:
        # Pending faces are not searchable.
        det.return_value = [synthetic_face(seed=1)]
        _, hits, _, _ = pipeline.search(synthetic_png(), limit=5)
        assert not [h for h in hits if h.payload["photo_id"] == pid]

    vector_store.set_photo_status(pid, vector_store.APPROVED)

    with patch("app.services.face_engine.analyze") as det:
        # Same embedding => must match itself once approved
        det.return_value = [synthetic_face(seed=1)]
        _, hits, _, _ = pipeline.search(synthetic_png(), limit=5)
        assert hits and hits[0].payload["photo_id"] == pid
        assert hits[0].score > 0.99

    with patch("app.services.face_engine.analyze") as det:
        # Different embedding => should NOT beat threshold
        det.return_value = [synthetic_face(seed=999)]
        _, hits, _, _ = pipeline.search(synthetic_png(), limit=5, threshold=0.0)
        for h in hits:
            assert h.score < 0.5


def test_ingest_raises_when_no_face():
    with patch("app.services.face_engine.analyze", return_value=[]):
        with pytest.raises(ValueError):
            pipeline.ingest(synthetic_png(), uploaded_by="olivia")


def test_metadata_stripped_and_filename_not_stored():
    raw = synthetic_jpeg_with_exif()
    assert Image.open(io.BytesIO(raw)).getexif()  # fixture really has EXIF
    with patch("app.services.face_engine.analyze", return_value=[synthetic_face(seed=31)]), \
         patch("app.services.rekognition.detect_faces", return_value=None) as rek:
        pid, _, _, _ = pipeline.ingest(raw, uploaded_by="olivia")
    stored = storage.load(pid)
    assert not Image.open(io.BytesIO(stored)).getexif()
    assert b"SyntheticCam" not in stored
    # Rekognition only ever sees the sanitized bytes.
    assert b"SyntheticCam" not in rek.call_args.args[0]
    payload = vector_store.faces_for_photo(pid)[0]
    assert "filename" not in payload
    assert set(payload) <= {
        "face_id", "photo_id", "bbox", "det_score", "quality",
        "review_status", "indexed_at", "uploaded_by", "model",
    }


def test_synthetic_marker_rejected_in_production(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "synthetic_data_enabled", False)
    with pytest.raises(ValueError, match="synthetic_data_rejected"):
        pipeline.prepare(synthetic_png())
