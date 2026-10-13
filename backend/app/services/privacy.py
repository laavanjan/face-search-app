"""Lawful-basis enforcement and the public processing record.

The legal basis is configured (DATA_PROCESSING_LEGAL_BASIS, a constrained
enum in app/config.py). When it is `consent`, upload and search are rejected
unless the caller affirms consent/authority for the image, and each
affirmation is written to the audit log with the notice version shown.
"""
from __future__ import annotations

from fastapi import HTTPException

from app.config import get_settings
from app.security import Principal
from app.services import audit

# Stated guarantee (governance/de-identification.yaml). No anonymisation is claimed.
PRIVACY_GUARANTEE = (
    "No k-anonymity or differential-privacy guarantee is provided. Face embeddings are "
    "re-identifiable biometric personal data. Protection relies on: role-based access, "
    "consent enforcement, human review before indexing and disclosure, metadata stripping, "
    "keyed pseudonyms for staff identities, encrypted appeal contacts, and retention limits."
)

PROCESSING_SCOPE = {
    "data_categories": [
        "uploaded photographs (re-encoded; EXIF/GPS/device metadata removed)",
        "face bounding boxes and detector/quality scores",
        "512-dimensional face embeddings (biometric data)",
        "search query photos (held only while the search is under human review)",
        "pseudonymous actor ids (keyed HMAC of the account name) in audit and review records",
        "appeal text and optional contact details (contact encrypted at rest)",
    ],
    "not_collected": [
        "original filenames",
        "image metadata (EXIF, GPS, camera serials)",
        "demographic attributes (age, gender, ethnicity) - never inferred",
    ],
    "purposes": [
        "find photos of a person within a private, authorised photo collection",
    ],
    "processors": {
        "local": ["InsightFace buffalo_l (on the API host)", "Qdrant (configured host)"],
        "optional_aws": ["Amazon Rekognition DetectFaces (quality scoring)", "Amazon S3 (photo storage)"],
    },
}


def require_lawful_basis(confirmed: bool, actor: Principal, purpose: str) -> None:
    s = get_settings()
    if s.data_processing_legal_basis == "consent" and not confirmed:
        raise HTTPException(
            422,
            "Consent confirmation required: confirm that everyone identifiable in this photo "
            f"has consented to face analysis (see {s.privacy_notice_url}).",
        )
    audit.record(
        actor,
        "lawful_basis.asserted",
        purpose,
        basis=s.data_processing_legal_basis,
        notice_version=s.privacy_notice_version,
        confirmed=confirmed,
    )


def policy() -> dict:
    s = get_settings()
    return {
        "legal_basis": s.data_processing_legal_basis,
        "consent_required": s.data_processing_legal_basis == "consent",
        "privacy_notice_url": s.privacy_notice_url,
        "privacy_notice_version": s.privacy_notice_version,
        "retention_days": {
            "photos_and_embeddings": s.photo_retention_days,
            "search_review_cases": s.review_case_retention_days,
            "resolved_appeals": s.appeal_retention_days,
            "audit_log": s.audit_log_retention_days,
        },
        "appeal_sla_days": {"acknowledge": s.appeal_ack_days, "resolve": s.appeal_resolution_days},
        "human_review": {
            "indexing_requires_approval": s.require_index_review,
            "search_results_require_approval": True,
        },
        "search_min_threshold": s.search_min_threshold,
        "search_max_limit": s.search_max_limit,
        "model": s.face_model_name,
        "uses_aws": s.use_rekognition or s.use_s3,
        "privacy_guarantee": PRIVACY_GUARANTEE,
        "processing_scope": PROCESSING_SCOPE,
    }
