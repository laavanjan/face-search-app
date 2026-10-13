# Change management, versioning and re-evaluation policy

| | |
|---|---|
| Owner | System Owner (@laavanjan) |
| Applies to | All code, configuration, models and data handling in this repository and its deployments |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

## 1. Versioning

- The API version is `FastAPI(version=...)` in `backend/app/main.py`; the frontend version is `frontend/package.json`. Both follow **semantic versioning**: MAJOR for breaking API or data-model changes, MINOR for new capability, PATCH for fixes.
- Every deployment is tagged `vX.Y.Z` in git. Each embedding in Qdrant records the `model` that produced it, so an index can always be traced to a model.
- Model identity is configuration, not code: `FACE_MODEL_NAME` and `FACE_DET_SIZE` (`backend/app/config.py`). The InsightFace package version is pinned in `backend/requirements.txt`.

## 2. Change classes

| Class | Examples | Required before merge/deploy |
|---|---|---|
| Minor | Copy, styling, refactor with no behaviour change, dependency patch | PR + Code Owner review + green CI |
| Material | Anything in the triggers below | PR + Code Owner review + **change record** in `docs/changes/` + re-evaluation evidence + admin approval in the running system |
| Major | New purpose, new data category, new third-party processor, new jurisdiction, lowering a human-review gate | Everything for *material* + updated [risk assessment](../risk/risk-assessment.md) + new [residual risk acceptance](../risk/residual-risk-acceptance.md) signed by the System Owner |

## 3. Re-evaluation triggers

A documented re-evaluation (template: [`docs/changes/TEMPLATE.md`](../changes/TEMPLATE.md)) is required **before** any of the following go live.

### 3.1 Model changes
- InsightFace model pack or version (`FACE_MODEL_NAME`, `insightface`/`onnxruntime` pins), execution provider, detector size (`FACE_DET_SIZE`) or embedding dimension (`vector_store.DIM`).
- Detection or matching thresholds: `MIN_DET_SCORE`, `MIN_FACE_SIZE`, `SEARCH_MIN_THRESHOLD`.
- Enabling, disabling or changing the Rekognition quality blend (`pipeline._cross_check_with_rekognition`).

Record: benchmark on the evaluation set (false-match and false-non-match rates, broken down by the
available demographic and image-quality slices), approval, rollout and rollback plan, and **re-indexing
impact** - embeddings from different models are not comparable, so a model change requires re-embedding
every stored photo before search is re-enabled.

### 3.2 Data changes
- Image preprocessing in `backend/app/services/pipeline.py`: EXIF transpose, RGB conversion, `MAX_DIM` resizing, re-encoding.
- Sources of indexed photos, what is stored by `storage.save` or written by `vector_store.upsert` (payload allowlist).
- The evaluation dataset, its labelling rules, or its composition.
- Retention periods or legal basis.

Record: a versioned evaluation-data manifest (source, consent/authorisation status, composition,
counts and hashes) and an accuracy, bias and privacy assessment.

### 3.3 Deployment changes
- Infrastructure or runtime (Docker image, Lambda via Mangum, Python version), Qdrant location (`QDRANT_URL`), S3 bucket or AWS region, `ALLOWED_ORIGINS`, public exposure, authentication configuration (`API_KEYS` structure, roles).

Record: configuration version, environment, smoke-test results (including `GET /health` showing
`config_approved: true`), approval, monitoring plan and rollback plan. A cross-border change also needs
an updated [transfer assessment](../privacy/cross-border-transfer-assessment.md).

### 3.4 After a serious incident
After any P0 or P1 incident ([incident-response.md](incident-response.md)) - for example unauthorised
photo or vector access, a materially wrong match acted on, harmful false positives, provider failure or
data loss:

1. Pause affected processing (`POST /admin/controls`) until the re-evaluation is complete.
2. Record impacted records and versions, preserve logs and configuration.
3. Assess whether `pipeline.ingest` / `pipeline.search` thresholds, the model, or the review gates need re-validation.
4. Add a regression test for the failure mode next to `backend/tests/` and link it from the incident record.
5. The System Owner approves resumption; the approval is recorded in the audit log.

## 4. How this is enforced

| Mechanism | Where |
|---|---|
| Code Owner review on every path | `.github/CODEOWNERS` + branch protection (owner must enable in GitHub settings) |
| PR fails if governance-sensitive files change without a new `docs/changes/CHG-*.md` | `.github/workflows/ci.yml` → job `change-record` |
| Running system refuses to index or search after a governance-sensitive config change until an admin approves it with a change id | `backend/app/services/controls.py` (`ensure_allowed`, `approve_config`), `POST /admin/config/approve` |
| PR checklist | `.github/pull_request_template.md` |

Governance-sensitive settings are listed in `Settings.governance_snapshot()` in `backend/app/config.py`.
