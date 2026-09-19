"""Smoke tests that don't require the InsightFace model to be downloaded."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_root():
    with TestClient(app) as c:
        r = c.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "face-search-api"


def test_health_shape():
    with patch("app.services.face_engine._get_app", return_value=None), \
         patch("app.services.vector_store.count", return_value=0):
        with TestClient(app) as c:
            r = c.get("/health")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            assert body["storage"] in {"s3", "local"}
            assert body["vector_store"] in {"qdrant-cloud", "qdrant-memory"}


def test_upload_rejects_wrong_type():
    with TestClient(app) as c:
        r = c.post(
            "/upload",
            files={"file": ("x.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 415
