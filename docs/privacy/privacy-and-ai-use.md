# Privacy notice, legal basis and AI use disclosure

| | |
|---|---|
| Notice version | 2026-10-14 (`PRIVACY_NOTICE_VERSION`) |
| Owner | Privacy & Incident Owner |
| Next review | 2027-01-14 |
| In-app | Persistent banner in `frontend/app/layout.tsx`; full page at `/privacy`; machine-readable at `GET /policy` |

## 1. AI use disclosure

Face Search is an **AI facial-recognition system**.

- **InsightFace `buffalo_l`** (run locally on the API host) detects faces and generates a **512-dimensional face embedding** for each qualifying face. Only the detection and recognition models are loaded - age, gender and landmark models in the pack are deliberately not run.
- **Qdrant** stores the embeddings and finds similar ones by cosine similarity.
- **Amazon Rekognition** is used, only when AWS is configured, to score face quality. It never decides identity.
- Similarity scores are **automated estimates, not identifications**. They can be wrong and may be less accurate for some groups of people. Every match is checked by a human reviewer before it is shown.

The same disclosure appears to users before they upload or search (index and search pages, layout banner).

## 2. Legal basis

| | |
|---|---|
| Configured basis | `DATA_PROCESSING_LEGAL_BASIS` - constrained to `consent`, `contract`, `legitimate_interest`, `legal_obligation`, `vital_interests`, `public_task` (`backend/app/config.py`) |
| Default / current | **`consent`** - and, for biometric (special-category) data, explicit consent |
| Enforcement | With `consent`, `POST /upload` and `POST /search` return 422 unless the operator ticks the (unchecked-by-default) consent confirmation. Each confirmation is audit-logged as `lawful_basis.asserted` with basis, notice version, actor and time (`backend/app/services/privacy.py`). |
| Changing the basis | Is a governance-sensitive change: processing pauses until an admin approves it ([change-management.md](../governance/change-management.md)) |

## 3. Scope of processing

| Category | Collected | Purpose | Where | Retention |
|---|---|---|---|---|
| Uploaded photo | Yes - **re-encoded**: EXIF, GPS, camera/device metadata and filename removed; resized to ≤ 1600 px | Show the photo to authorised users and reviewers | Local disk or private S3 | `PHOTO_RETENTION_DAYS` (90) |
| Face embedding (512-d) | Yes - biometric | Similarity search | Qdrant | Same as photo |
| Face bbox, detector score, quality score | Yes | Reviewer evidence, ranking | Qdrant payload | Same as photo |
| Review status, indexed-at time, uploader pseudonym, model name | Yes | Oversight gate, TTL, separation of duties, traceability | Qdrant payload | Same as photo |
| Search reference photo | Yes, temporarily | Reviewer compares it with candidates | Governance DB | Deleted when the case closes; case record `REVIEW_CASE_RETENTION_DAYS` (30) |
| Appeal text | Yes | Recourse | Governance DB | `APPEAL_RETENTION_DAYS` (365) after resolution |
| Appeal contact (email/phone, optional) | Yes - encrypted | Send the decision | Governance DB | `APPEAL_CONTACT_RETENTION_DAYS` (30) after resolution |
| Audit log (pseudonymous actor id, action, opaque target id, reason) | Yes | Accountability | Governance DB | `AUDIT_LOG_RETENTION_DAYS` (365) |
| Original filename, EXIF/GPS, inferred age/gender/ethnicity/emotion | **No** | - | - | - |

Purpose limitation: photos and embeddings are used only to find a person within the collection. They
are never used for training, benchmarking, profiling, or export ([training-data.md](training-data.md)).

## 4. Recipients

None by default. When configured: AWS (Rekognition, S3) as processor - see
[cross-border-transfer-assessment.md](cross-border-transfer-assessment.md). Qdrant Cloud if `QDRANT_URL`
points to it.

## 5. Rights

Access, deletion, objection and correction via `/appeal` (no account needed) - see
[appeals-and-sla.md](../oversight/appeals-and-sla.md).
