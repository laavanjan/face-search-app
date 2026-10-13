# CHG-XXXX: <title>

| | |
|---|---|
| Date | YYYY-MM-DD |
| Requested by | |
| Approved by (System Owner) | |
| Class | minor / material / major |
| Release | vX.Y.Z |
| Triggers ([change-management.md §3](../governance/change-management.md)) | model / data / deployment / incident |

## What changes
Settings, files, components. For config: old → new values from `GET /admin/controls` → `pending_diff`.

## Re-evaluation
- Model / threshold: evaluation set (manifest link), FMR / FNMR overall and by group, before vs after.
- Data: source, consent status, composition, counts, hashes.
- Deployment: environment, config version, smoke test (`GET /health` → `config_approved: true`).
- Privacy: new data, new recipients, transfer assessment.

## Re-indexing impact
None / re-embed all photos (plan + downtime).

## Risk
Register rows touched; new risks.

## Rollout and rollback
Steps, monitoring, rollback.

## Approval
Admin approval recorded in-app with this id: `POST /admin/config/approve {"change_id": "CHG-XXXX", ...}` (if config changed).
