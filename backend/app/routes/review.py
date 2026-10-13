"""Reviewer endpoints - the human approval gates for indexing and disclosure."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.models.schemas import CandidateDecision, CaseClose, ManualMatch, PhotoDecision, Reason
from app.security import Principal, require_permissions
from app.services import review

router = APIRouter(prefix="/review")
reviewer = require_permissions("review:decide")


@router.get("/photos")
def pending_photos(limit: int = Query(100, ge=1, le=500), _: Principal = Depends(reviewer)):
    return {"items": review.pending_photos(limit)}


@router.post("/photos/{photo_id}")
def decide_photo(photo_id: str, body: PhotoDecision, p: Principal = Depends(reviewer)):
    return review.decide_photo(photo_id, body.decision, p, body.reason)


@router.get("/cases")
def list_cases(status: Optional[str] = "pending_review", _: Principal = Depends(reviewer)):
    return {"items": review.list_cases(status or None)}


@router.get("/cases/{case_id}")
def get_case(case_id: str, _: Principal = Depends(reviewer)):
    return review.get_case(case_id)


@router.get("/cases/{case_id}/query-image")
def case_query_image(case_id: str, _: Principal = Depends(reviewer)):
    data, media = review.query_image(case_id)
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, no-store"})


@router.post("/cases/{case_id}/candidates/{face_id}")
def decide_candidate(case_id: str, face_id: str, body: CandidateDecision, p: Principal = Depends(reviewer)):
    return review.decide_candidate(case_id, face_id, body.decision, p, body.reason)


@router.post("/cases/{case_id}/manual-match")
def manual_match(case_id: str, body: ManualMatch, p: Principal = Depends(reviewer)):
    return review.add_manual_match(case_id, body.photo_id, p, body.reason)


@router.post("/cases/{case_id}/close")
def close_case(case_id: str, body: CaseClose, p: Principal = Depends(reviewer)):
    return review.close_case(case_id, body.outcome, p, body.reason)


@router.post("/cases/{case_id}/reopen")
def reopen_case(case_id: str, body: Reason, p: Principal = Depends(reviewer)):
    return review.reopen_case(case_id, p, body.reason)
