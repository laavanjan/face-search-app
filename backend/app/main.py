import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.routes import photos, search, upload
from app.services import face_engine, storage, vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        face_engine._get_app()  # noqa: SLF001
    except Exception as e:  # noqa: BLE001
        logging.getLogger(__name__).warning("Face engine warm-up deferred: %s", e)
    yield


app = FastAPI(
    title="Face Search API",
    version="0.1.0",
    description="Upload photos, search by face. InsightFace + Qdrant, optional AWS Rekognition/S3.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, tags=["index"])
app.include_router(search.router, tags=["search"])
app.include_router(photos.router, tags=["photos"])


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health():
    detector = "insightface"
    if settings.use_rekognition:
        detector += "+rekognition"
    return HealthResponse(
        status="ok",
        detector=detector,
        storage=storage.backend_name(),
        vector_store=vector_store.backend_name(),
        indexed_faces=vector_store.count(),
    )


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "face-search-api",
        "docs": "/docs",
        "health": "/health",
    }


# AWS Lambda entrypoint (used by Mangum in deploy).
try:
    from mangum import Mangum

    handler = Mangum(app)
except Exception:  # noqa: BLE001
    handler = None
