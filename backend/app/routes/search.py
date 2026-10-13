from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config import get_settings
from app.models.schemas import BoundingBox, SearchCaseResponse, SearchMatch
from app.routes.common import CaseId, pipeline_error, read_image
from app.security import Principal, current_principal, require_permissions
from app.services import controls, explain, pipeline, privacy, provenance, review, storage

router = APIRouter()


@router.post("/search", response_model=SearchCaseResponse)
async def search(
    file: UploadFile = File(...),
    limit: int = Form(20, ge=1, le=200),
    threshold: float = Form(0.35, ge=0.0, le=1.0),
    consent: bool = Form(False),
    p: Principal = Depends(require_permissions("photos:search")),
):
    """Opens a review case. Candidates are never returned directly: they are
    released by GET /search/cases/{case_id} after a reviewer completes it."""
    controls.ensure_allowed("search")
    s = get_settings()
    # The caller cannot lower the bar below the governed minimum.
    applied = max(float(threshold), s.search_min_threshold)
    limit = max(1, min(int(limit), s.search_max_limit))
    data = await read_image(file)
    privacy.require_lawful_basis(consent, p, "search")
    try:
        faces, hits, clean, ext = pipeline.search(data, limit=limit, threshold=applied)
    except Exception as e:  # noqa: BLE001
        raise pipeline_error(e, "No face detected in reference photo") from e
    case = review.create_case(p, applied, len(faces), hits, clean, ext)
    return SearchCaseResponse(
        case_id=case["case_id"],
        status=case["status"],
        query_faces=len(faces),
        threshold_applied=applied,
        candidate_count=case["candidate_count"],
        matches=[],
    )


@router.get("/search/cases/{case_id}", response_model=SearchCaseResponse)
def search_case(case_id: CaseId, p: Principal = Depends(current_principal)):
    r = review.released_matches(case_id, p)
    th = r["threshold_applied"]
    matches = []
    for m in r["matches"]:
        band = explain.confidence_band(m["score"], th)
        matches.append(
            SearchMatch(
                photo_id=m["photo_id"],
                face_id=m["face_id"],
                url=storage.public_url(m["photo_id"]),
                score=m["score"],
                bbox=BoundingBox(x=m["bbox"][0], y=m["bbox"][1], w=m["bbox"][2], h=m["bbox"][3]),
                source=m["source"],
                reviewed_by=m["decided_by"],
                confidence_band=band,
                band_meaning=explain.BAND_MEANING[band],
            )
        )
    body = {"case_id": case_id, "status": r["status"], "matches": [m.model_dump() for m in matches]}
    return SearchCaseResponse(
        case_id=r["case_id"],
        status=r["status"],
        query_faces=r["query_faces"],
        threshold_applied=th,
        matches=matches,
        limitations=explain.CAVEATS,
        provenance=provenance.stamp(body, subject=f"case:{case_id}", human_reviewed=r["status"] == "completed"),
    )


@router.get("/search/cases/{case_id}/explain")
def explain_case(case_id: CaseId, p: Principal = Depends(current_principal)):
    """Why each released match was proposed (TRAN-03). Released matches only."""
    r = review.released_matches(case_id, p)
    return {
        "case_id": case_id,
        "status": r["status"],
        "approach": "evidence-based: similarity, threshold margin, confidence band, detector/quality scores, human decision",
        "explanations": [
            explain.explain_candidate(m, r["threshold_applied"], explain.face_for(m)) for m in r["matches"]
        ],
    }
