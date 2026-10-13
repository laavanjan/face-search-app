"""Qdrant wrapper. Falls back to an in-memory client when QDRANT_URL is blank,
so local dev works without any external service.

Payload allowlist (data minimisation - every field has a consumer):
  photo_id       join key to the stored photo (opaque, server-generated)
  bbox           reviewer UI + search result overlay
  det_score      reviewer evidence
  quality        reviewer evidence / ranking
  review_status  human-oversight gate: only "approved" faces are searchable
  indexed_at     retention TTL (governance/data-retention-policy.yaml)
  uploaded_by    separation of duties (uploader cannot approve own upload)
  model          ties the embedding to the model that produced it (re-index on change)
No filenames, EXIF or free text are stored.
"""
from __future__ import annotations

import logging
import threading
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.config import get_settings
from app.services.resilience import retry

log = logging.getLogger(__name__)

_client: QdrantClient | None = None
_lock = threading.Lock()
DIM = 512

PENDING, APPROVED, DISPUTED = "pending", "approved", "disputed"


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client
    with _lock:
        if _client is None:
            s = get_settings()
            if s.qdrant_url:
                log.info("Connecting to remote Qdrant.")  # URL may embed credentials
                client = QdrantClient(
                    url=s.qdrant_url,
                    api_key=s.qdrant_api_key or None,
                    timeout=s.qdrant_timeout_seconds,
                )
            else:
                log.info("QDRANT_URL blank - using in-memory Qdrant.")
                client = QdrantClient(":memory:")
            retry(lambda: _ensure_collection(client), op="qdrant.ensure_collection")
            _client = client
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


def _photo_filter(photo_id: str) -> qm.Filter:
    return qm.Filter(must=[qm.FieldCondition(key="photo_id", match=qm.MatchValue(value=photo_id))])


def upsert(
    photo_id: str,
    face_id: str,
    embedding: list[float],
    bbox: tuple[int, int, int, int],
    det_score: float,
    quality: float,
    review_status: str,
    indexed_at: float,
    uploaded_by: str,
) -> None:
    s = get_settings()
    client = _get_client()
    point = qm.PointStruct(
        id=face_id,
        vector=embedding,
        payload={
            "photo_id": photo_id,
            "bbox": list(bbox),
            "det_score": det_score,
            "quality": quality,
            "review_status": review_status,
            "indexed_at": indexed_at,
            "uploaded_by": uploaded_by,
            "model": s.face_model_name,
        },
    )
    retry(
        lambda: client.upsert(collection_name=s.qdrant_collection, points=[point]),
        op="qdrant.upsert",
    )


def search(embedding: list[float], limit: int = 20, score_threshold: float = 0.35):
    """Similarity search over human-approved faces only."""
    s = get_settings()
    client = _get_client()
    flt = qm.Filter(
        must=[qm.FieldCondition(key="review_status", match=qm.MatchValue(value=APPROVED))]
    )
    return retry(
        lambda: client.search(
            collection_name=s.qdrant_collection,
            query_vector=embedding,
            query_filter=flt,
            limit=limit,
            score_threshold=score_threshold,
        ),
        op="qdrant.search",
    )


def count() -> int:
    s = get_settings()
    try:
        return _get_client().count(collection_name=s.qdrant_collection).count
    except Exception:
        return 0


def new_id() -> str:
    return str(uuid.uuid4())


def _scroll(flt: qm.Filter | None = None):
    s = get_settings()
    client = _get_client()
    offset = None
    while True:
        points, offset = retry(
            lambda: client.scroll(
                collection_name=s.qdrant_collection,
                scroll_filter=flt,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            ),
            op="qdrant.scroll",
        )
        yield from points
        if offset is None:
            return


def faces_for_photo(photo_id: str) -> list[dict]:
    return [{"face_id": str(p.id), **(p.payload or {})} for p in _scroll(_photo_filter(photo_id))]


def photos(limit: int = 200, status: str | None = None) -> list[dict]:
    """Distinct photos with their faces, newest first."""
    flt = None
    if status:
        flt = qm.Filter(
            must=[qm.FieldCondition(key="review_status", match=qm.MatchValue(value=status))]
        )
    grouped: dict[str, dict] = {}
    for p in _scroll(flt):
        pl = p.payload or {}
        pid = pl.get("photo_id")
        if not pid:
            continue
        g = grouped.setdefault(
            pid,
            {
                "photo_id": pid,
                "review_status": pl.get("review_status"),
                "indexed_at": pl.get("indexed_at"),
                "uploaded_by": pl.get("uploaded_by"),
                "faces": [],
            },
        )
        g["faces"].append(
            {
                "face_id": str(p.id),
                "bbox": pl.get("bbox"),
                "det_score": pl.get("det_score"),
                "quality": pl.get("quality"),
            }
        )
    items = sorted(grouped.values(), key=lambda g: g["indexed_at"] or 0, reverse=True)
    return items[:limit]


def set_photo_status(photo_id: str, status: str) -> int:
    s = get_settings()
    n = len(faces_for_photo(photo_id))
    if n:
        retry(
            lambda: _get_client().set_payload(
                collection_name=s.qdrant_collection,
                payload={"review_status": status},
                points=_photo_filter(photo_id),
            ),
            op="qdrant.set_payload",
        )
    return n


def delete_by_photo_id(photo_id: str) -> int:
    s = get_settings()
    n = len(faces_for_photo(photo_id))
    if n:
        retry(
            lambda: _get_client().delete(
                collection_name=s.qdrant_collection,
                points_selector=qm.FilterSelector(filter=_photo_filter(photo_id)),
            ),
            op="qdrant.delete",
        )
    return n


def expired_photo_ids(cutoff_ts: float) -> set[str]:
    flt = qm.Filter(must=[qm.FieldCondition(key="indexed_at", range=qm.Range(lt=cutoff_ts))])
    return {(p.payload or {}).get("photo_id") for p in _scroll(flt)} - {None}


def migrate_legacy_payloads(now: float) -> int:
    """Bring points written before the governance changes into line:
    drop `filename`, stamp `indexed_at` (starts the TTL), and send faces with
    no review status back through human review."""
    s = get_settings()
    client = _get_client()
    fixed = 0
    for p in _scroll():
        pl = p.payload or {}
        patch = {}
        if "indexed_at" not in pl:
            patch["indexed_at"] = now
        if "review_status" not in pl:
            patch["review_status"] = PENDING
        if patch:
            client.set_payload(collection_name=s.qdrant_collection, payload=patch, points=[p.id])
        if "filename" in pl:
            client.delete_payload(collection_name=s.qdrant_collection, keys=["filename"], points=[p.id])
        if patch or "filename" in pl:
            fixed += 1
    if fixed:
        log.info("Migrated %d legacy vector payload(s).", fixed)
    return fixed
