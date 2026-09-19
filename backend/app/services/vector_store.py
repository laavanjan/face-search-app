"""Qdrant wrapper. Falls back to an in-memory client when QDRANT_URL is blank,
so local dev works without any external service."""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import get_settings

log = logging.getLogger(__name__)

_client: QdrantClient | None = None
_lock = threading.Lock()
DIM = 512


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is None:
            s = get_settings()
            if s.qdrant_url:
                log.info("Connecting to Qdrant at %s", s.qdrant_url)
                _client = QdrantClient(
                    url=s.qdrant_url,
                    api_key=s.qdrant_api_key or None,
                    timeout=20.0,
                )
            else:
                log.info("QDRANT_URL blank - using in-memory Qdrant.")
                _client = QdrantClient(":memory:")
            _ensure_collection(_client)
    return _client


def _ensure_collection(client: QdrantClient) -> None:
    s = get_settings()
    existing = {c.name for c in client.get_collections().collections}
    if s.qdrant_collection not in existing:
        client.create_collection(
            collection_name=s.qdrant_collection,
            vectors_config=qm.VectorParams(size=DIM, distance=qm.Distance.COSINE),
        )


def backend_name() -> str:
    return "qdrant-cloud" if get_settings().qdrant_url else "qdrant-memory"


def upsert(
    photo_id: str,
    face_id: str,
    embedding: list[float],
    bbox: tuple[int, int, int, int],
    det_score: float,
    quality: float,
    filename: str,
) -> None:
    s = get_settings()
    client = _get_client()
    client.upsert(
        collection_name=s.qdrant_collection,
        points=[
            qm.PointStruct(
                id=face_id,
                vector=embedding,
                payload={
                    "photo_id": photo_id,
                    "filename": filename,
                    "bbox": list(bbox),
                    "det_score": det_score,
                    "quality": quality,
                },
            )
        ],
    )


def search(embedding: list[float], limit: int = 20, score_threshold: float = 0.35):
    s = get_settings()
    client = _get_client()
    return client.search(
        collection_name=s.qdrant_collection,
        query_vector=embedding,
        limit=limit,
        score_threshold=score_threshold,
    )


def count() -> int:
    s = get_settings()
    try:
        return _get_client().count(collection_name=s.qdrant_collection).count
    except Exception:
        return 0


def new_id() -> str:
    return str(uuid.uuid4())


def all_photos(limit: int = 200) -> list[dict]:
    """Distinct photo payloads for the gallery view."""
    s = get_settings()
    client = _get_client()
    seen: dict[str, dict] = {}
    offset = None
    while len(seen) < limit:
        points, offset = client.scroll(
            collection_name=s.qdrant_collection,
            limit=100,
            offset=offset,
            with_payload=True,
        )
        for p in points:
            pl = p.payload or {}
            pid = pl.get("photo_id")
            if pid and pid not in seen:
                seen[pid] = {
                    "photo_id": pid,
                    "filename": pl.get("filename"),
                    "quality": pl.get("quality"),
                }
        if offset is None:
            break
    return list(seen.values())[:limit]
