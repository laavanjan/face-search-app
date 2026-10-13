# Incident response runbook

| | |
|---|---|
| Owner | Privacy & Incident Owner (interim: @laavanjan) |
| Last reviewed | 2026-10-14 |
| Next review | 2027-01-14 |

## 1. Severity levels

| Severity | Criteria (this system) | Examples | Response target | Decision authority |
|---|---|---|---|---|
| **P0 - critical** | Exposure, loss or unauthorised use of face photos, embeddings or appeal contact data; or a wrong match acted on with harm to a person | Leaked API key used to read photos; public S3 bucket; Qdrant reachable without auth; data loss of `./data/photos` or Qdrant | Acknowledge 1 h; contain 4 h | System Owner |
| **P1 - major** | Core function down or a human-review gate not working | `/upload` or `/search` failing for all users; Qdrant unavailable; review gate bypass; retention sweep failing > 24 h; AWS Rekognition/S3 failing when enabled | Acknowledge 4 h; fix or workaround 1 business day | System Owner |
| **P2 - minor** | Degraded quality or monitoring, core function available | Detector quality drift; slow inference (504s); `StatusBar` health display wrong; weekly monitoring run failing | Acknowledge 2 business days; fix next release | Human Reviewer or System Owner |

When in doubt, classify higher and downgrade later.

## 2. Escalation matrix

Personal phone numbers and emails are deliberately kept out of the repository. Contact via the
channels below; the oversight register lists the current assignee for each role.

| Severity | First responder | Escalate to | Then | Channel | Acknowledge within |
|---|---|---|---|---|---|
| P0 | On-call / System Owner | Privacy & Incident Owner | Affected people + regulator if required (see §5) | GitHub private security advisory on `laavanjan/face-search-app` | 1 h |
| P1 | System Owner | Human Reviewer (if review gate involved); infra owner for Qdrant/AWS | - | GitHub issue labelled `incident` + `P1` | 4 h |
| P2 | Human Reviewer or System Owner | System Owner | - | GitHub issue labelled `incident` + `P2` | 2 business days |

## 3. Runbook

### Detect
- `GET /health` - `status`, `storage`, `vector_store`, `indexing_paused`, `search_paused`, `config_approved`.
- Backend logs (stdout; format set in `backend/app/logging_setup.py`, personal data redacted).
- Audit log: `GET /admin/audit` (admin) - who approved, deleted, paused, what config was approved.
- Weekly monitoring workflow failure issues; appeals flagged `overdue`.

### Triage
1. Classify severity (table above). Open the issue/advisory and note the time.
2. Identify scope: which endpoints, which photo ids (audit log targets), which time window.

### Contain
- **Stop processing first**: `POST /admin/controls {"indexing_paused": true, "search_paused": true, "reason": "INC-…"}` or the Admin console.
- Leaked key: remove the entry from `API_KEYS`, restart the backend; issue a new key.
- Exposed storage: make the S3 bucket private / block public access; restrict Qdrant network access and rotate `QDRANT_API_KEY`.
- A wrong match acted on: reopen or stop the case (`/review`), mark the photo disputed via an appeal, inform the requester.

### Recover
- Check `QDRANT_URL` reachability and the `./data/qdrant` volume; restart the `qdrant` container.
- Check the `./data/photos` and `./data/governance` volumes (or S3 bucket) are intact; restore from backup if needed.
- Roll back: redeploy the previous tagged backend image (`docker compose up -d --build` from the previous tag).
- If AWS is enabled: verify Rekognition/S3 credentials and region in the deployment env.
- Resume with `POST /admin/controls` only after the System Owner approves (re-evaluation rules in [change-management.md §3.4](change-management.md)).

### Communicate
- P0 involving personal data: inform affected people without undue delay with what happened, what data, what we did, and how to appeal. Assess regulator notification (GDPR: within 72 h of awareness where required).
- Close-out note in the issue/advisory.

### Post-incident review (within 5 business days of P0/P1)
Timeline, root cause, what worked and what did not, regression test added in `backend/tests/`, risk
register updated, re-evaluation record in `docs/changes/` if a model/threshold/config changed.

## 4. Logs to preserve
Audit log rows for the window, backend logs, deployment env (minus secrets), Qdrant snapshot if relevant.

## 5. Notification obligations
See [regulatory applicability](../compliance/regulatory-applicability.md) for breach-notification duties per jurisdiction.
