"""Smoke tests that don't require the InsightFace model to be downloaded."""
from unittest.mock import patch

from tests.conftest import OPERATOR


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "face-search-api"


def test_health_shape(client):
    with patch("app.services.vector_store.count", return_value=0):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["storage"] in {"s3", "local"}
        assert body["vector_store"] in {"qdrant-cloud", "qdrant-memory"}
        assert body["model"] == "buffalo_l"
        # Operational counts are not public.
        assert body["indexed_faces"] is None
        assert client.get("/health", headers=OPERATOR).json()["indexed_faces"] == 0


def test_upload_rejects_wrong_type(client):
    r = client.post(
        "/upload",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers=OPERATOR,
    )
    assert r.status_code == 415


def test_policy_is_public(client):
    body = client.get("/policy").json()
    assert body["legal_basis"] == "consent"
    assert body["human_review"]["search_results_require_approval"] is True
    assert body["retention_days"]["photos_and_embeddings"] > 0
