from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.schemas import UploadResponse
from app.routes.common import pipeline_error, read_image
from app.security import Principal, require_permissions
from app.services import audit, controls, pipeline, privacy

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload(
    file: UploadFile = File(...),
    consent: bool = Form(False),
    p: Principal = Depends(require_permissions("photos:write")),
):
    controls.ensure_allowed("indexing")
    data = await read_image(file)
    privacy.require_lawful_basis(consent, p, "upload")
    try:
        photo_id, url, faces, status = pipeline.ingest(data, uploaded_by=p.ref)
    except Exception as e:  # noqa: BLE001
        raise pipeline_error(e, "No face detected in this photo") from e
    audit.record(p, "photo.upload", photo_id, faces=len(faces), review_status=status)
    pending = status == "pending"
    return UploadResponse(
        photo_id=photo_id,
        url=url,
        faces=faces,
        review_status=status,
        message=f"Indexed {len(faces)} face(s)"
        + (" - awaiting reviewer approval before it is searchable" if pending else ""),
    )
