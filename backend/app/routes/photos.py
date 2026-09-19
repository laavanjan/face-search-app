from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services import storage, vector_store

router = APIRouter()


@router.get("/photos/{photo_id}")
def get_photo(photo_id: str):
    try:
        data = storage.load(photo_id)
    except FileNotFoundError as e:
        raise HTTPException(404, "Photo not found") from e
    ext = photo_id.rsplit(".", 1)[-1].lower() if "." in photo_id else "jpeg"
    return Response(content=data, media_type=f"image/{ext}")


@router.get("/gallery")
def gallery(limit: int = 100):
    items = vector_store.all_photos(limit=limit)
    for it in items:
        it["url"] = storage.public_url(it["photo_id"])
    return {"count": len(items), "items": items}
