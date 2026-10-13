# Data retention and deletion policy

| | |
|---|---|
| Owner | Privacy & Incident Owner |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |
| Code | `backend/app/services/retention.py`, `backend/app/jobs/retention.py`, `backend/app/config.py` |

This schedule is public (also served at `GET /policy` and shown at `/privacy`).

## Retention schedule

| Data | Store | Retention | Setting | Deleted by |
|---|---|---|---|---|
| Uploaded photos (sanitized) | `LOCAL_PHOTO_DIR` or S3 `photos/` | **90 days** from indexing | `PHOTO_RETENTION_DAYS` | TTL sweep |
| Face embeddings + payload | Qdrant collection | Same as the photo; deleted together | `PHOTO_RETENTION_DAYS` | TTL sweep (`indexed_at` < cutoff) |
| Search reference photos | Governance DB (`review_cases.query_image`) | Until the case is closed (completed / no_match / stopped) | - | `review.close_case`; sweep clears leftovers |
| Search review cases + candidates | Governance DB | **30 days** | `REVIEW_CASE_RETENTION_DAYS` | TTL sweep |
| Resolved appeals | Governance DB | **365 days** after resolution | `APPEAL_RETENTION_DAYS` | TTL sweep |
| Audit log | Governance DB | **365 days** | `AUDIT_LOG_RETENTION_DAYS` | TTL sweep |
| Application logs | stdout / log platform | ≤ 30 days on the log platform; personal data redacted at source | Platform setting | Platform |

The longest any biometric data is kept is 90 days, well inside BIPA's 3-year ceiling.

## Mechanisms

- **Scheduled cleanup**: the API runs `retention.purge_expired()` at start-up and every `RETENTION_SWEEP_INTERVAL_MINUTES` (60). On AWS Lambda, schedule `python -m app.jobs.retention` with EventBridge (hourly). An admin can run it on demand (`POST /admin/retention/run`).
- **S3 lifecycle (defence in depth)**: when S3 is enabled, also add a lifecycle rule expiring `photos/` objects after `PHOTO_RETENTION_DAYS + 1` days, and block public access on the bucket.
- **One deletion path**: `retention.delete_photo()` removes the stored image, **every** Qdrant point for that `photo_id`, and any pending review candidates. TTL expiry, `DELETE /photos/{id}`, index-review rejection and appeal resolution all call it, so request-driven and expiry-driven deletion behave identically.
- **Legacy data**: on start-up, points written before this policy are stamped with `indexed_at` (starting their TTL), returned to `pending` review, and stripped of the old `filename` field (`vector_store.migrate_legacy_payloads`).

## Deletion requests

| Route | Who | Completion |
|---|---|---|
| `DELETE /photos/{photo_id}?reason=…` | `admin` (`photos:delete`) | Immediate |
| Appeal `deletion_request` → resolve with `delete_photo` | Reviewer files the decision; admin executes | Photo restricted immediately; erased within the 30-day appeal SLA |
| Reviewer rejects at index review | `reviewer` | Immediate |

Every deletion is written to the audit log (`photo.delete`, actor, reason).

## Exceptions

- **Legal hold**: if an incident or legal claim requires preservation, the System Owner pauses the sweep for the affected scope (stop the sweeper / raise the TTL through an approved config change) and records the hold in the incident issue. Holds are reviewed monthly.
- **Backups**: if Qdrant snapshots or disk backups are taken, they must expire within 30 days so deleted data does not outlive the policy by more than that.

## Verification

`backend/tests/test_governance.py::test_delete_endpoint_removes_file_and_vectors`,
`test_retention_ttl_purges_expired_photos`, `test_reject_at_index_review_deletes_photo`,
`test_deletion_appeal_needs_delete_permission`.
