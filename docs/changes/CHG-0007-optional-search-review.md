# CHG-0007: Optional human review of search results (REQUIRE_SEARCH_REVIEW)

| | |
|---|---|
| Date | 2026-11-25 |
| Requested by | @laavanjan |
| Approved by (System Owner) | @laavanjan |
| Class | material |
| Release | v0.2.1 |
| Triggers | deployment, config |

## What changes
- New setting `REQUIRE_SEARCH_REVIEW` (default `true`, so behaviour is unchanged unless it is switched off).
- With `false`, `POST /search` completes the case at once: candidates are stored as approved by `auto:no-review`, the query photo is not retained, and the audit log records `search.case_auto_released` instead of `search.case_created`.
- Matches returned this way carry `reviewed_by: null` and `provenance.human_reviewed: false`; the search page says "not human-checked". The public transparency report and privacy summary report the setting.
- `require_search_review` is part of the governance snapshot (`config.governance_snapshot`), so changing it pauses indexing and search until an admin approves.
- Files: `backend/app/config.py`, `services/review.py`, `routes/search.py`, `routes/support.py`, `services/privacy.py`, `frontend/app/search/page.tsx`, `backend/.env.example`, `governance/human-approval-gates.yaml`, tests.

## Re-evaluation
- Model / threshold: unchanged.
- Data: none new. Fewer review cases are stored when the setting is off.
- Deployment: production is switched off for a single-owner deployment (`REQUIRE_SEARCH_REVIEW=false`, `REQUIRE_INDEX_REVIEW=false`, `ALLOW_SELF_REVIEW=true` on the host).
- Privacy: removes the human check before a match is disclosed to the person who searched. Accepted by the owner for a single-user deployment with photos of consenting people only.

## Re-indexing impact
None.

## Risk
- A wrong match is shown without a second person looking at it. Mitigations: the UI says matches are not human-checked, the confidence band and limitations are still shown, the consent and permitted-purpose checks still apply, everything is audited, and the setting defaults to on.
- Do not switch this off for a deployment with more than one trusted user or with photos of people who have not agreed.

## Rollout and rollback
Deploy, set `REQUIRE_SEARCH_REVIEW=false` in `/opt/face-search/backend.env`, restart the backend, then an admin approves the config change. Roll back by setting it to `true` (or removing the line) and restarting.

## Approval
Admin approval recorded in-app with this id: `POST /admin/config/approve {"change_id": "CHG-0007", ...}`.
