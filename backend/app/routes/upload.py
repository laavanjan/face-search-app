from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.models.schemas import UploadResponse
from app.routes.common import pipeline_error, read_image
from app.security import Principal, require_permissions
from app.services import audit, controls, pipeline, privacy, provenance

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
    audit.record(p, "photo.upload", photo_id, decision=status,
                 evidence={"faces": [{"face_id": f.face_id, "det_score": round(f.det_score, 4), "quality": round(f.quality, 4)} for f in faces]})
    pending = status == "pending"
    return UploadResponse(
        photo_id=photo_id,
        url=url,
        faces=faces,
        review_status=status,
        provenance=provenance.stamp(
            {"photo_id": photo_id, "faces": [f.model_dump() for f in faces], "review_status": status},
            subject=f"photo:{photo_id}",
            human_reviewed=False,
        ),
        message=f"Indexed {len(faces)} face(s)"
        + (" - awaiting reviewer approval before it is searchable" if pending else ""),
    )
