import asyncio
import logging
from contextlib import asynccontextmanager, suppress
import time
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.logging_setup import configure_logging
from app.models.schemas import HealthResponse
from app.routes import admin, appeals, photos, review, search, upload
from app.security import Principal, configured_principals, current_principal, optional_principal
from app.tracing import TraceMiddleware
from app.services import controls, crypto, face_engine, privacy, retention, storage, vector_store

configure_logging()
log = logging.getLogger(__name__)

settings = get_settings()


async def _retention_loop() -> None:
    loop = asyncio.get_running_loop()
    while True:
        try:
            await loop.run_in_executor(None, retention.purge_expired)
        except Exception as e:  # noqa: BLE001
            log.error("retention_sweep failed: %s", type(e).__name__)
        await asyncio.sleep(settings.retention_sweep_interval_minutes * 60)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()  # re-attach redaction to uvicorn's handlers
    crypto.check_key()
    if not configured_principals():
        log.warning("API_KEYS is empty: every protected endpoint will answer 401.")
    elif any("change-me" in k for k in settings.api_keys.split(",")):
        log.warning("API_KEYS still contains example tokens; replace them before any shared deployment.")
    controls.bootstrap_baseline()
    if not controls.config_status()["approved"]:
        log.warning("Governance-sensitive config changed: indexing + search paused until an admin approves.")
    try:
        vector_store.migrate_legacy_payloads(time.time())
    except Exception as e:  # noqa: BLE001
        log.warning("Legacy payload migration deferred: %s", type(e).__name__)
    try:
        face_engine._get_app()  # noqa: SLF001
    except Exception as e:  # noqa: BLE001
        log.warning("Face engine warm-up deferred: %s", type(e).__name__)
    sweeper = asyncio.create_task(_retention_loop())
    yield
    sweeper.cancel()
    with suppress(asyncio.CancelledError):
        await sweeper


app = FastAPI(
    title="Face Search API",
    version="0.2.0",
    description=(
        "Consent-based face search over a private photo collection. InsightFace + Qdrant, "
        "optional AWS Rekognition/S3. Biometric processing - see GOVERNANCE.md for intended "
        "and prohibited use. Indexing and result disclosure are gated by human review."
    ),
    lifespan=lifespan,
)

# Added last = outermost: every request gets a trace ID before anything else runs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(TraceMiddleware)  # TRAN-05: trace ID at the entry point

# Authentication is the default for every data-bearing router; each route then
# adds its specific permission. Only meta routes and the two appeal routes
# (submit + status lookup) are public - see tests/test_governance.py
# ::test_every_route_requires_auth_except_allowlist.
authenticated = [Depends(current_principal)]
app.include_router(upload.router, tags=["index"], dependencies=authenticated)
app.include_router(search.router, tags=["search"], dependencies=authenticated)
app.include_router(photos.router, tags=["photos"], dependencies=authenticated)
app.include_router(review.router, tags=["review"], dependencies=authenticated)
app.include_router(appeals.router, tags=["appeals"], dependencies=authenticated)
app.include_router(admin.router, tags=["admin"], dependencies=authenticated)
app.include_router(appeals.public_router, tags=["appeals"])


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(p: Optional[Principal] = Depends(optional_principal)):
    detector = "insightface"
    if settings.use_rekognition:
        detector += "+rekognition"
    c = controls.summary()
    return HealthResponse(
        status="ok",
        detector=detector,
        model=settings.face_model_name,
        storage=storage.backend_name(),
        vector_store=vector_store.backend_name(),
        indexing_paused=c["indexing_paused"],
        search_paused=c["search_paused"],
        config_approved=c["config"]["approved"],
        indexed_faces=vector_store.count() if p else None,
    )


@app.get("/auth/me", tags=["meta"])
def whoami(p: Principal = Depends(current_principal)):
    return {"name": p.name, "ref": p.ref, "roles": list(p.roles), "permissions": sorted(p.permissions)}


@app.get("/policy", tags=["meta"])
def policy():
    """Public processing record: legal basis, retention, review gates, SLA."""
    return privacy.policy()


@app.get("/", tags=["meta"])
def root():
    return {
        "name": "face-search-api",
        "docs": "/docs",
        "health": "/health",
        "policy": "/policy",
        "appeals": "/appeals",
    }


# AWS Lambda entrypoint (used by Mangum in deploy).
try:
    from mangum import Mangum

    handler = Mangum(app)
except Exception:  # noqa: BLE001
    handler = None
