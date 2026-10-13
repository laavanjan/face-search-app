# CHG-0002: Audit #49 remediation

| | |
|---|---|
| Date | 2026-10-14 |
| Requested by | Agent audit report #49 (commit e6e630d) |
| Approved by (System Owner) | @laavanjan |
| Class | material |
| Release | v0.2.1 |
| Triggers | data, deployment |

## What changes
- **Machine-readable governance records** in `governance/*.yaml` (incident response, change management, regulatory mapping, risk assessment, ranked ethical impacts, oversight roles, approval gates, retention, de-identification, model provenance, synthetic-data bias). Validated by `scripts/check_governance.py`. The Markdown docs remain the human-readable versions.
- **PRIV-01**: staff identities stored as keyed HMAC pseudonyms (audit log, review records, vector payloads); appeal contacts validated, encrypted at rest, wiped 30 days after resolution. New dependency `cryptography==43.0.3`; new settings `DATA_ENCRYPTION_KEY`, `APPEAL_CONTACT_RETENTION_DAYS`.
- **PRIV-05**: authentication is a router-level default; only meta routes and appeal submit/status are public (route-coverage test). Multi-role keys need `ALLOWED_ROLE_BUNDLES`; `ENVIRONMENT=production` refuses raw tokens and starts only with `DATA_ENCRYPTION_KEY`.
- **HUMO-02**: pause/config gate also enforced inside `pipeline.ingest` / `pipeline.search`.
- **GOV-01**: CI job `codeowner-approval`; branch protection declared in `.github/settings.yml`.

## Re-evaluation
Model, thresholds and retention periods unchanged, so the config fingerprint is unchanged. Backend tests: 42 passing.

## Re-indexing impact
None. Existing audit rows keep the old account names until they expire under `AUDIT_LOG_RETENTION_DAYS`. Existing appeal contacts written before this change are plaintext; they are wiped by the 30-day contact sweep after resolution.

## Rollout and rollback
Set `DATA_ENCRYPTION_KEY` before deploying, and never change it afterwards: pseudonyms and encrypted contacts depend on it. Rollback: redeploy v0.2.0.
