# Changelog

Versions are pinned in `backend/app/version_manifest.json` (code, model, data schema, prompts).
Each release is tagged `vX.Y.Z`; material changes have a record in `docs/changes/`.

## 0.2.1 - 2026-10-14
- Security: deny-by-default auth middleware, global rate limit, abuse-report endpoint, no hard-coded keys,
  secret scanning, SBOM and dependency audit in CI, Dependabot, threat model, vulnerability policy (CHG-0004).
- Audit log: append-only (SQLite triggers) with a SHA-256 hash chain and `GET /admin/audit/verify` (CHG-0004).
- Versioning: version manifest, `GET /version`, DB schema version in `PRAGMA user_version` (CHG-0004).
- Fairness, transparency and safety controls: fairness evaluation/monitoring, trace IDs, decision rationale,
  explanations, provenance, input validation, red-team tests (CHG-0003).
- Pseudonymous staff ids, encrypted appeal contacts, router-level auth, governance YAML records (CHG-0002).

## 0.2.0 - 2026-10-14
- Governance, human oversight and privacy controls: RBAC, review gates, appeals, retention, consent (CHG-0001).

## 0.1.0
- Initial face search: upload, search, gallery; InsightFace + Qdrant; optional Rekognition/S3.
