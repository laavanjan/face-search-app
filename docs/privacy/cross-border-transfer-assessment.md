# Cross-border data transfer assessment

| | |
|---|---|
| Owner | Privacy & Incident Owner |
| Date | 2026-10-14 |
| Next review | 2027-01-14, and before enabling any item marked "transfer" below |

## 1. Data flows

| Flow | Default | Data | Transfer? |
|---|---|---|---|
| Browser → backend API | On | Photos, search photos | Within the deployment's own hosting region |
| Backend → local disk (`LOCAL_PHOTO_DIR`) | On (when S3 blank) | Sanitized photos | No |
| Backend → Qdrant in-memory / docker | On (when `QDRANT_URL` blank or local) | Embeddings | No |
| Backend → InsightFace model download (first run) | On | None outbound (download only) | No personal data |
| Backend → **Amazon Rekognition** (`AWS_REGION`) | **Off** | Sanitized image bytes | **Yes, if `AWS_REGION` is outside the data subjects' jurisdiction** |
| Backend → **Amazon S3** (`S3_BUCKET_NAME`, `AWS_REGION`) | **Off** | Sanitized photos | **Same as above** |
| Backend → **Qdrant Cloud** (`QDRANT_URL`) | Off | Embeddings + payload | **Yes, if cluster region differs** |

**Current determination (default configuration): no cross-border transfer occurs.**

## 2. Before enabling a transfer

Complete and commit a filled-in copy of this checklist as a change record (`docs/changes/CHG-xxxx.md`):

1. Data subjects' jurisdiction(s) and the destination region (`AWS_REGION`, Qdrant cluster region). Prefer a region in the same jurisdiction (e.g. `eu-central-1` / `eu-west-1` for EU subjects); then no transfer occurs.
2. Transfer mechanism if crossing borders: adequacy decision, or Standard Contractual Clauses (AWS GDPR DPA includes SCCs) plus a transfer impact assessment.
3. **Opt out of AWS AI-service content use** (AWS Organizations "AI services opt-out policy") before Rekognition processes any image.
4. Confirm only sanitized bytes leave the host (`pipeline.prepare` - enforced in code).
5. S3: block public access, SSE-KMS encryption, lifecycle expiry per [data-retention-policy.md](data-retention-policy.md).
6. Update [privacy-and-ai-use.md §4](privacy-and-ai-use.md) recipients and the `/privacy` page.
7. Admin approval in the running system: enabling AWS changes `use_rekognition` / `use_s3` / `aws_region` in `Settings.governance_snapshot()`, so indexing and search stay paused until `POST /admin/config/approve` with the change id.

## 3. Residual risk
Tracked as R-05 in the [risk register](../risk/risk-register.md).
