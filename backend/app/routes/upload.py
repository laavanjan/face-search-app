from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services import pipeline

router = APIRouter()

ALLOWED = {"image/jpeg", "image/png", "image/webp"}


@router.post("/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"Unsupported type {file.content_type}")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Max 15MB per photo")
    try:
        photo_id, url, faces = pipeline.ingest(data, file.filename or "upload.jpg")
    except ValueError as e:
        if str(e) == "no_face_detected":
            raise HTTPException(422, "No face detected in this photo") from e
        raise
    return UploadResponse(
        photo_id=photo_id,
        url=url,
        faces=faces,
        message=f"Indexed {len(faces)} face(s)",
    )
