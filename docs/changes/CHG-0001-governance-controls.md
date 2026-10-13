# CHG-0001: Governance, oversight and privacy controls (audit remediation)

| | |
|---|---|
| Date | 2026-10-14 |
| Requested by | Agent audit report, 2026-10-13 (commit 8bdfc5b) |
| Approved by (System Owner) | _pending - @laavanjan_ |
| Class | **major** (new access model, new human-review gates, new data handling) |
| Release | v0.2.0 |
| Triggers | data, deployment |

## What changes
- Deny-by-default RBAC with per-role API keys (`API_KEYS`); all data routes protected; photos served only via authenticated `/photos/{id}`.
- Human review gates: uploads `pending` until approved; search returns a review case and releases only reviewer-approved matches; stop / escalate / manual takeover; separation of duties.
- Admin stop switch and configuration-approval gate.
- Appeals with immediate restriction; SLA fields.
- Retention TTL sweep, `DELETE /photos/{id}`, single deletion path.
- Upload sanitisation (EXIF/GPS/filename removed) before storage and before AWS; Qdrant payload allowlist; age/gender models no longer loaded; log redaction.
- Legal-basis enum + consent enforcement + audit; public `GET /policy`.
- Inference deadline; bounded retries; AWS timeouts.
- Governance documents under `docs/`, `GOVERNANCE.md`, CODEOWNERS, CI and scheduled monitoring.

## Re-evaluation
- Model and thresholds unchanged (`buffalo_l`, `MIN_DET_SCORE=0.5`, `MIN_FACE_SIZE=40`). Search floor fixed at the previous default 0.35 - behaviour change: callers can no longer go below it.
- Data: fewer data collected (filename, EXIF, attributes removed). No new recipients.
- Tests: 37 passing (`cd backend && pytest`); frontend `next build` passes.

## Re-indexing impact
None for embeddings. Existing points are migrated on start-up: `filename` removed, `indexed_at` set, `review_status=pending` → **existing photos need reviewer approval before they are searchable again.**

## Risk
Register created (R-01-R-11). Tier: High.

## Rollout and rollback
1. Copy new variables from `backend/.env.example`; issue real per-person keys.
2. Deploy; confirm `/health` and approve pending photos.
Rollback: redeploy v0.1.0 (data written by v0.2.0 remains compatible; the governance DB is ignored by v0.1.0).
