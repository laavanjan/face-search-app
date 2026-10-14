# CHG-0004: Security and traceability controls (audit #50, SEC/DOC)

| | |
|---|---|
| Date | 2026-10-14 |
| Requested by | Agent audit report #50 (commit f1009fe) |
| Approved by (System Owner) | @laavanjan |
| Class | material |
| Release | v0.2.1 |
| Triggers | deployment, data |

## What changes
- **Auth + abuse (SEC-01, SEC-04)**: `AuthGateMiddleware` (deny-by-default before routing), `RateLimitMiddleware` (`RATE_LIMIT_PER_MINUTE`, default 300), `POST /abuse-reports`; the hard-coded development encryption key is replaced by a random per-process key (production still requires `DATA_ENCRYPTION_KEY`).
- **Membership-inference fix (SEC-07)**: every search now goes to a reviewer, even with zero candidates, and `candidate_count` is no longer returned to requesters - previously the response revealed whether a person was in the library before review.
- **Supply chain (SEC-03, SEC-05)**: `.github/workflows/security.yml` (gitleaks, CycloneDX SBOM, pip-audit/npm audit, hash-pinned lockfile check), `.github/dependabot.yml`, `.gitleaks.toml`, `SECURITY.md`, branch-protection checks in `.github/settings.yml`.
- **Audit log (DOC-04, DOC-07)**: append-only triggers + SHA-256 hash chain, `GET /admin/audit/verify`, verification at start-up; rationale now has explicit `inputs` and `output`.
- **Versioning (DOC-05)**: `backend/app/version_manifest.json`, `GET /version`, `PRAGMA user_version`, `CHANGELOG.md`; frontend version 0.2.1.
- **Records**: threat model, LLM-usage statement, supply-chain, vulnerability management, pretrained-model assessment, privacy-attack assessment, system overview, audit-log integrity; model card and retention policy extended.

## Re-evaluation
Model, thresholds and retention periods unchanged. 110 backend tests pass.

## Data / schema
Migration adds `audit_log.prev_hash` / `row_hash`, back-fills the chain for existing rows, installs the triggers and sets `PRAGMA user_version = 3`.

## Follow-up required
`backend/requirements.lock` must be committed from the `lockfile` job artifact of `security.yml` (could not be generated locally: unreliable network to PyPI). Until then that job fails by design.

## Rollout and rollback
Rollback to v0.2.0 is possible, but first drop the triggers `audit_log_no_update` and `audit_log_expire_oldest_only`: v0.2.0's retention sweep deletes audit rows in bulk, which the oldest-first trigger may refuse.
