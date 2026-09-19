from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import BoundingBox, SearchMatch, SearchResponse
from app.services import pipeline, storage

router = APIRouter()

ALLOWED = {"image/jpeg", "image/png", "image/webp"}


@router.post("/search", response_model=SearchResponse)
async def search(
    file: UploadFile = File(...),
    limit: int = Form(20),
    threshold: float = Form(0.35),
):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"Unsupported type {file.content_type}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    try:
        faces, hits = pipeline.search(data, limit=limit)
    except ValueError as e:
        if str(e) == "no_face_detected":
            raise HTTPException(422, "No face detected in reference photo") from e
        raise

    matches: list[SearchMatch] = []
    for h in hits:
        if h.score < threshold:
            continue
        pl = h.payload or {}
        bx = pl.get("bbox") or [0, 0, 0, 0]
        matches.append(
            SearchMatch(
                photo_id=pl["photo_id"],
                face_id=str(h.id),
                url=storage.public_url(pl["photo_id"]),
                score=float(h.score),
                bbox=BoundingBox(x=bx[0], y=bx[1], w=bx[2], h=bx[3]),
            )
        )
    return SearchResponse(query_faces=len(faces), matches=matches)
