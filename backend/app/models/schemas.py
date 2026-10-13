from typing import Literal, Optional

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class FaceRecord(BaseModel):
    face_id: str
    photo_id: str
    bbox: BoundingBox
    det_score: float
    quality: float = Field(description="Sharpness / detector confidence, 0-1")


class UploadResponse(BaseModel):
    photo_id: str
    url: str
    faces: list[FaceRecord]
    review_status: str = Field(description="pending = awaiting human approval before it is searchable")
    message: str
    provenance: Optional[dict] = Field(None, description="Signed provenance block (services/provenance.py)")


class SearchMatch(BaseModel):
    photo_id: str
    face_id: str
    url: str
    score: Optional[float] = Field(description="Cosine similarity; null for a reviewer-added match")
    bbox: BoundingBox
    source: Literal["model", "human"]
    reviewed_by: Optional[str] = None
    confidence_band: Literal["low", "medium", "high", "human"] = Field(
        description="How far above the threshold the score is; 'low' = the system is uncertain"
    )
    band_meaning: str


class SearchCaseResponse(BaseModel):
    case_id: str
    status: str
    query_faces: int
    threshold_applied: float
    candidate_count: Optional[int] = None
    matches: list[SearchMatch] = Field(
        description="Only human-approved matches, and only once the case is completed."
    )
    notice: str = (
        "AI-generated similarity candidates are not identifications. "
        "Matches are released only after human review."
    )
    limitations: list[str] = Field(default_factory=list, description="User-facing limitations (TRAN-02)")
    provenance: Optional[dict] = Field(None, description="Signed provenance block (services/provenance.py)")


class HealthResponse(BaseModel):
    status: str
    detector: str
    model: str
    storage: str
    vector_store: str
    indexing_paused: bool
    search_paused: bool
    config_approved: bool
    indexed_faces: Optional[int] = Field(None, description="Only shown to authenticated callers")


class Reason(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class PhotoDecision(Reason):
    decision: Literal["approve", "reject"]


class CandidateDecision(Reason):
    decision: Literal["approve", "reject", "reopen"]


class CaseClose(Reason):
    outcome: Literal["completed", "no_match", "stopped", "escalated"]


PHOTO_ID = r"^[0-9a-f]{32}\.(jpg|jpeg|png|webp)$"


class ManualMatch(Reason):
    photo_id: str = Field(pattern=PHOTO_ID)


class AppealRequest(BaseModel):
    category: Literal["incorrect_match", "indexing_objection", "deletion_request", "access_request", "other"]
    reason: str = Field(min_length=10, max_length=2000)
    photo_id: Optional[str] = Field(None, pattern=PHOTO_ID)
    face_id: Optional[str] = Field(None, max_length=80, pattern=r"^[0-9a-z:.-]+$")
    case_id: Optional[str] = Field(None, pattern=r"^[0-9a-f]{32}$")
    contact: Optional[str] = Field(
        None,
        max_length=200,
        pattern=r"^([^@\s]+@[^@\s]+\.[^@\s]+|\+?[0-9 ()-]{7,20})$",
        description="Optional email or phone; encrypted at rest and used only to reply",
    )


class AppealResolve(BaseModel):
    outcome: Literal["upheld", "partially_upheld", "rejected"]
    resolution: str = Field(min_length=3, max_length=2000)
    action: Literal["none", "delete_photo", "restore_photo"] = "none"


class ControlsUpdate(Reason):
    indexing_paused: Optional[bool] = None
    search_paused: Optional[bool] = None


class ConfigApproval(Reason):
    change_id: str = Field(min_length=3, max_length=64, description="e.g. CHG-0002 in docs/changes/")
