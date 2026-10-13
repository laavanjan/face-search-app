import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LegalBasis = Literal[
    "consent",
    "contract",
    "legitimate_interest",
    "legal_obligation",
    "vital_interests",
    "public_task",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = ""
    s3_bucket_name: str = ""

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "faces"

    # Model identity. Changing these requires re-evaluation and re-indexing
    # (governance/change-management.yaml).
    face_model_name: str = "buffalo_l"
    face_det_size: int = 640

    min_face_size: int = 40
    min_det_score: float = 0.5

    local_photo_dir: str = "./data/photos"
    allowed_origins: str = "http://localhost:3000"

    # development | production. Production rejects raw API tokens (sha256 only).
    environment: Literal["development", "production"] = "development"

    # --- Access control (governance/oversight-roles.yaml) ---
    # Comma-separated "name:role:token". The token may be written as
    # "sha256:<hex>" so the raw secret never sits in the env file.
    # Empty = no principals = every protected endpoint answers 401.
    api_keys: str = ""
    # Multi-role keys are refused unless the exact bundle is allowlisted here,
    # e.g. "operator+reviewer". Empty = one role per key.
    allowed_role_bundles: str = ""

    # Secret for audit pseudonyms (HMAC) and appeal-contact encryption.
    # Derived sub-keys are used for each purpose. Must be set in production.
    data_encryption_key: str = ""

    # --- Human oversight gates ---
    require_index_review: bool = True
    allow_self_review: bool = False
    search_min_threshold: float = 0.35
    search_max_limit: int = 50

    # --- Privacy (governance/de-identification.yaml) ---
    data_processing_legal_basis: LegalBasis = "consent"
    privacy_notice_url: str = "/privacy"
    privacy_notice_version: str = "2026-10-14"

    # --- Retention (governance/data-retention-policy.yaml) ---
    photo_retention_days: int = 90
    review_case_retention_days: int = 30
    appeal_retention_days: int = 365
    audit_log_retention_days: int = 365
    appeal_contact_retention_days: int = 30  # contact wiped this long after resolution
    retention_sweep_interval_minutes: int = 60

    # --- Recourse SLA (docs/oversight/appeals-and-sla.md) ---
    appeal_ack_days: int = 2
    appeal_resolution_days: int = 30

    # Test-only: accept images tagged as synthetic (governance/synthetic-data-bias-assessment.yaml).
    synthetic_data_enabled: bool = False

    governance_db_path: str = "./data/governance.db"

    # --- Reliability: deadlines + bounded retries ---
    qdrant_timeout_seconds: float = 20.0
    aws_connect_timeout_seconds: float = 5.0
    aws_read_timeout_seconds: float = 20.0
    aws_max_attempts: int = 3
    remote_retry_attempts: int = 3
    inference_timeout_seconds: float = 60.0

    @property
    def use_s3(self) -> bool:
        return bool(self.s3_bucket_name and self.aws_access_key_id)

    @property
    def use_rekognition(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_region)

    @property
    def photo_dir(self) -> Path:
        p = Path(self.local_photo_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def db_path(self) -> Path:
        p = Path(self.governance_db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def governance_snapshot(self) -> dict:
        """Settings that change matching behaviour or data handling.

        If any of these differ from the last approved snapshot, indexing and
        search stay paused until an admin approves the change
        (app/services/controls.py).
        """
        return {
            "face_model_name": self.face_model_name,
            "face_det_size": self.face_det_size,
            "min_face_size": self.min_face_size,
            "min_det_score": self.min_det_score,
            "search_min_threshold": self.search_min_threshold,
            "require_index_review": self.require_index_review,
            "allow_self_review": self.allow_self_review,
            "use_rekognition": self.use_rekognition,
            "use_s3": self.use_s3,
            "aws_region": self.aws_region,
            "data_processing_legal_basis": self.data_processing_legal_basis,
            "photo_retention_days": self.photo_retention_days,
        }

    def governance_fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.governance_snapshot(), sort_keys=True).encode()).hexdigest()


@lru_cache
def get_settings() -> Settings:
    return Settings()
