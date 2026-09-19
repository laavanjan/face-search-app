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
    message: str


class SearchMatch(BaseModel):
    photo_id: str
    face_id: str
    url: str
    score: float
    bbox: BoundingBox


class SearchResponse(BaseModel):
    query_faces: int
    matches: list[SearchMatch]


class HealthResponse(BaseModel):
    status: str
    detector: str
    storage: str
    vector_store: str
    indexed_faces: int
