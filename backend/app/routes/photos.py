from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.config import get_settings
from app.security import Principal, require_permissions
from app.services import retention, storage, vector_store

router = APIRouter()

DAY = 86400


@router.get("/photos/{photo_id}", dependencies=[Depends(require_permissions("photos:read"))])
def get_photo(photo_id: str):
    try:
        data = storage.load(photo_id)
    except FileNotFoundError as e:
        raise HTTPException(404, "Photo not found") from e
    ext = photo_id.rsplit(".", 1)[-1].lower()
    media = "image/jpeg" if ext in {"jpg", "jpeg"} else f"image/{ext}"
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, no-store"})


@router.delete("/photos/{photo_id}")
def delete_photo(
    photo_id: str,
    reason: str = Query(..., min_length=3, max_length=500),
    p: Principal = Depends(require_permissions("photos:delete")),
):
    """Erase the stored photo and every face vector derived from it."""
    if not storage.valid_photo_id(photo_id):
        raise HTTPException(404, "Photo not found")
    result = retention.delete_photo(photo_id, p, reason)
    if not result["vectors_deleted"] and not result["file_deleted"]:
        raise HTTPException(404, "Photo not found")
    return result


@router.get("/gallery", dependencies=[Depends(require_permissions("photos:read"))])
def gallery(limit: int = Query(100, ge=1, le=500), status: Optional[str] = None):
    ttl = get_settings().photo_retention_days * DAY
    items = []
    for g in vector_store.photos(limit=limit, status=status):
        items.append(
            {
                "photo_id": g["photo_id"],
                "url": storage.public_url(g["photo_id"]),
                "review_status": g["review_status"],
                "indexed_at": g["indexed_at"],
                "expires_at": (g["indexed_at"] or 0) + ttl,
                "face_count": len(g["faces"]),
                "quality": max((f["quality"] or 0) for f in g["faces"]),
            }
        )
    return {"count": len(items), "items": items}
