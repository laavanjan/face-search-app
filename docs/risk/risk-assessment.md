# Risk and impact assessment (initial project risk assessment / DPIA)

| | |
|---|---|
| System | Face Search API + web UI, v0.2.0 |
| Owner | System Owner (@laavanjan) |
| Assessment date | 2026-10-14 |
| Review cadence | Quarterly, and on every trigger in [reassessment-policy.md](reassessment-policy.md) |
| Next review | 2027-01-14 |
| **Risk tier** | **HIGH** (scale: low / medium / high) |

## 1. Application domain

**Domain: consumer and organisational photo management - biometric face identification.** The system
is a face-recognition photo search: `face_engine.py` produces 512-d ArcFace embeddings, `pipeline.py`
stores them in Qdrant, and the UI lets a user find every photo containing a person from one reference
photo.

**Intended deployment:** consent-based indexing of a private photo library (personal, family, or an
organisation's own event photos with attendee consent).

**Out of scope unless separately assessed and approved:** public surveillance, CCTV, law enforcement or
border identification, employment, housing, credit, insurance, education, healthcare, or any other
decision with legal or similarly significant effect. See [GOVERNANCE.md §3](../../GOVERNANCE.md).

## 2. Risk tier and reasoning

**Tier: High.**

1. **Special-category data.** Face embeddings are biometric identifiers (GDPR Art. 9; BIPA). They cannot be revoked like a password.
2. **1:N identification.** `/search` compares one face to the whole library - functionally the same capability that the EU AI Act lists as high-risk remote biometric identification.
3. **Non-users are affected.** Bystanders in uploaded photos never interact with the system.
4. **Third parties.** When configured, images go to AWS Rekognition and S3 (`config.py` → `use_rekognition`, `use_s3`), which adds transfer and processor risk.
5. **Error is harmful.** A false match discloses a photo of the wrong person; error rates for face recognition are known to differ across demographic groups.

Mitigations reduce likelihood but not the inherent severity, so the tier stays High regardless of controls.

## 3. Stakeholders

| Stakeholder | Impact | Accountable owner |
|---|---|---|
| Photo uploaders / operators | Upload and search; may act on a wrong match | System Owner |
| People depicted in uploaded photos (incl. non-users, bystanders, minors) | Biometric indexing; findability; misidentification | Human Reviewer (indexing gate) |
| Person in the search reference photo | Biometric comparison against the library | Human Reviewer |
| Search-result subjects | Disclosure of their photo to the requester | Human Reviewer (disclosure gate) |
| Administrators / deployment operators | Hold keys, run deletion, approve config | System Owner |
| AWS (Rekognition, S3) - when configured | Receives/stores images | Privacy Owner |
| Qdrant (self-hosted or cloud) | Stores embeddings | System Owner |
| InsightFace / model provider | Licence terms over weights | System Owner |

Full analysis: [stakeholder-impact-assessment.md](../governance/stakeholder-impact-assessment.md).

## 4. Scale and environment

### Environment
- Local / single-host Docker: `docker-compose.yml` runs Qdrant (`./data/qdrant`), the FastAPI backend (`./data/photos`, `./data/governance`), and the Next.js frontend. In-memory Qdrant when `QDRANT_URL` is blank.
- Optional: AWS Lambda via Mangum, Qdrant Cloud, S3 + Rekognition.

### Current and planned scale (assumptions to validate)

| Dimension | Current (dev) | Approved maximum without re-assessment |
|---|---|---|
| Authorised users (keys) | ≤ 5 | 10 |
| Photos uploaded / day | < 50 | 500 |
| Faces indexed / day | < 200 | 2,000 |
| Retained photos | < 1,000 | 20,000 (≈ 90-day TTL × daily cap) |
| Retained vectors | < 5,000 | 100,000 |
| Searches / day (each creates a review case) | < 20 | 200 (bounded by reviewer capacity) |
| Concurrent searches | 1-2 | 5 |

### Limits already in code
- Uploads ≤ 15 MB, resized to `MAX_DIM = 1600` px (`pipeline.py`).
- One 512-d embedding per qualifying face (`MIN_DET_SCORE`, `MIN_FACE_SIZE`).
- Search: at most `SEARCH_MAX_LIMIT` (50) candidates, similarity ≥ `SEARCH_MIN_THRESHOLD` (0.35).
- Model inference deadline `INFERENCE_TIMEOUT_SECONDS` (60 s).

Exceeding the approved maximum, enabling S3/Rekognition for production, or moving from personal to
organisational use requires a renewed assessment.

## 5. Ethical impacts - ranked

Ranked by severity × likelihood **after** current controls (1 = highest priority).

| # | Impact | Why it ranks here (tied to the implementation) | Mitigation (implemented → evidence) | Residual | Owner | Review |
|---|---|---|---|---|---|---|
| 1 | **Unauthorised biometric collection** - people indexed without consent | `/upload` persists embeddings for every detected face, including bystanders | Consent confirmation required + logged (`privacy.require_lawful_basis`); faces `pending` and unsearchable until a reviewer approves (`review.decide_photo`); TTL deletion; objection via `/appeal` immediately excludes the photo | Medium - consent is asserted by the operator, not each subject | System Owner | Quarterly |
| 2 | **False-positive identification disclosed** | `/search` ranks by cosine similarity; a caller could previously lower `threshold` to 0 | Floor `SEARCH_MIN_THRESHOLD` enforced server-side; results are candidates only; released only after a reviewer approves each and completes the case (`review.released_matches`); "Report incorrect match" on every result | Medium-low | Human Reviewer | Quarterly |
| 3 | **Disparate performance across demographic groups** | `buffalo_l` training data composition is not documented per group; no fairness evaluation exists in this repo | Human verification of every match; fairness evaluation required before any threshold/model change ([change-management.md](../governance/change-management.md)); synthetic tests explicitly not used for accuracy claims | **High - no measurement yet** (register R-03) | System Owner | Before next threshold change |
| 4 | **Unauthorised access / disclosure of photos and biometric templates** | Previously no auth on any route; S3 URLs were public-style | Deny-by-default RBAC on every data route; photos only via authenticated `/photos/{id}`; photo-id validation; log redaction; `/health` hides counts | Low-medium (keys are static bearer tokens) | System Owner | Monthly access review |
| 5 | **Third-party transfer to AWS** | `rekognition.py` sends image bytes to AWS; `storage.py` writes to S3 | Off by default; only sanitized (EXIF-stripped) bytes sent; transfer assessment + AI-services opt-out required before enabling; config gate pauses processing when AWS settings change | Low (when off) | Privacy Owner | On enablement |
| 6 | **Function creep / harmful downstream use** (surveillance, profiling) | A search tool can be repurposed | Prohibited-use policy shown in UI; audit log of every search; reviewer can stop a case; no attribute inference models loaded | Medium | System Owner | Quarterly |
| 7 | **Over-retention** | Photos, vectors and query images were kept forever | TTL sweep; query images deleted when a case closes; appeal and audit retention limits | Low | Privacy Owner | Quarterly |
| 8 | **Availability / quality failures** (model stall, Qdrant outage) | Lazy model load and CPU inference could hang requests | Inference deadline → 504; bounded retries on Qdrant; botocore timeouts/retries; `/health`; incident runbook | Low | System Owner | Monthly |

## 6. Residual risk and verification

| Control | Verified by |
|---|---|
| RBAC deny-by-default | `tests/test_governance.py::test_protected_endpoints_deny_anonymous`, `test_least_privilege` |
| Index approval gate | `test_upload_is_pending_until_reviewer_approves`, `test_reject_at_index_review_deletes_photo` |
| Disclosure gate, stop, takeover | `test_search_results_released_only_after_review`, `test_stop_prevents_release`, `test_human_takeover_manual_match` |
| Separation of duties | `test_separation_of_duties`, `test_other_operator_cannot_read_case` |
| Deletion + retention | `test_delete_endpoint_removes_file_and_vectors`, `test_retention_ttl_purges_expired_photos` |
| Minimisation | `tests/test_pipeline.py::test_metadata_stripped_and_filename_not_stored` |
| Config approval gate | `test_config_change_requires_approval` |

Residual risk is accepted (time-limited) in [residual-risk-acceptance.md](residual-risk-acceptance.md);
all open risks are tracked in [risk-register.md](risk-register.md).
