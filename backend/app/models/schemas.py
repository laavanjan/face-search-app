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


class SearchMatch(BaseModel):
    photo_id: str
    face_id: str
    url: str
    score: Optional[float] = Field(description="Cosine similarity; null for a reviewer-added match")
    bbox: BoundingBox
    source: Literal["model", "human"]
    reviewed_by: Optional[str] = None


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


class ManualMatch(Reason):
    photo_id: str


class AppealRequest(BaseModel):
    category: Literal["incorrect_match", "indexing_objection", "deletion_request", "access_request", "other"]
    reason: str = Field(min_length=10, max_length=2000)
    photo_id: Optional[str] = Field(None, max_length=64)
    face_id: Optional[str] = Field(None, max_length=80)
    case_id: Optional[str] = Field(None, max_length=64)
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
